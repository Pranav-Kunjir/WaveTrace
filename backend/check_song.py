from collections import defaultdict
import math
import os
import sqlite3
from pathlib import Path

from main import Process_audio
from storage import DATABASE_PATH


def match_song(audio_file="./untitled.wav"):
    process = Process_audio(audio_file)
    process.convert_stereo_to_mono()
    process.low_pass_filter_tensor()
    resampled_filename = process.resample()
    _, peaks = process.caclulate_spectogram(resampled_filename)

    query_hashes = {}
    process.calculate_hashes(peaks, 5, "query", query_hashes)
    query_hash_count = max(len(query_hashes), 1)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(DISTINCT songID) FROM SONG_DATA")
        song_count = max(cursor.fetchone()[0], 1)

        matched_pairs_by_song = defaultdict(list)
        matched_hashes_by_song = defaultdict(set)
        raw_hash_matches_by_song = defaultdict(int)
        weighted_hash_matches_by_song = defaultdict(float)

        for hash_id, query_points in query_hashes.items():
            cursor.execute(
                """
                SELECT time, song_id
                FROM FINGERPRINT
                WHERE hash = ?
                """,
                (hash_id,),
            )
            db_matches = cursor.fetchall()

            if not db_matches:
                continue

            songs_with_hash = {song_id for _, song_id in db_matches}
            rarity_weight = math.log(
                (song_count + 1) / (len(songs_with_hash) + 1)
            ) + 1

            for query_time, _ in query_points:
                for db_time, song_id in db_matches:
                    matched_pairs_by_song[song_id].append((query_time, db_time))
                    matched_hashes_by_song[song_id].add(hash_id)
                    raw_hash_matches_by_song[song_id] += 1
                    weighted_hash_matches_by_song[song_id] += rarity_weight

        results = []
        timing_threshold = 100
        offset_tolerance = 5

        for song_id in matched_hashes_by_song:
            pairs = sorted(
                set(matched_pairs_by_song[song_id]),
                key=lambda pair: (pair[0], pair[1]),
            )

            offset_counts = defaultdict(int)
            for query_time, database_time in pairs:
                offset_counts[database_time - query_time] += 1

            dominant_offset = max(
                offset_counts,
                key=offset_counts.get,
                default=0,
            )
            aligned_pairs = [
                pair
                for pair in pairs
                if abs((pair[1] - pair[0]) - dominant_offset) <= offset_tolerance
            ]

            # A query frame can match many database rows for the same hash.
            # Keep one aligned database position per query frame so repeated
            # collisions cannot inflate a candidate's timing evidence.
            best_pair_by_query_frame = {}
            for pair in aligned_pairs:
                query_frame = pair[0]
                current_pair = best_pair_by_query_frame.get(query_frame)
                current_distance = (
                    abs(current_pair[1] - current_pair[0] - dominant_offset)
                    if current_pair is not None
                    else None
                )
                pair_distance = abs(pair[1] - pair[0] - dominant_offset)
                if current_pair is None or pair_distance < current_distance:
                    best_pair_by_query_frame[query_frame] = pair

            aligned_pairs = sorted(best_pair_by_query_frame.values())
            dominant_offset_count = len(aligned_pairs)

            timing_score = 0
            for index in range(len(aligned_pairs) - 1):
                query_gap = abs(
                    aligned_pairs[index + 1][0] - aligned_pairs[index][0]
                )
                database_gap = abs(
                    aligned_pairs[index + 1][1] - aligned_pairs[index][1]
                )

                if abs(query_gap - database_gap) <= timing_threshold:
                    timing_score += 1

            timing_comparisons = max(len(aligned_pairs) - 1, 1)
            timing_consistency = timing_score / timing_comparisons
            hash_coverage = len(matched_hashes_by_song[song_id]) / query_hash_count

            results.append({
                "song_id": song_id,
                "hash_matches": raw_hash_matches_by_song[song_id],
                "matched_hashes": len(matched_hashes_by_song[song_id]),
                "aligned_matches": len(aligned_pairs),
                "dominant_offset_count": dominant_offset_count,
                "hash_coverage": hash_coverage,
                "timing_score": timing_score,
                "timing_consistency": timing_consistency,
                "weighted_hash_matches": weighted_hash_matches_by_song[song_id],
                "first_match_frame": aligned_pairs[0][1] if aligned_pairs else 0,
            })

        if not results:
            return []

        max_aligned_matches = max(
            result["aligned_matches"] for result in results
        )
        max_offset_count = max(
            result["dominant_offset_count"] for result in results
        )
        max_timing_score = max(
            result["timing_score"] for result in results
        )

        for result in results:
            aligned_score = (
                result["aligned_matches"] / max_aligned_matches
                if max_aligned_matches > 0
                else 0.0
            )
            offset_score = (
                result["dominant_offset_count"] / max_offset_count
                if max_offset_count > 0
                else 0.0
            )
            timing_score = (
                result["timing_score"] / max_timing_score
                if max_timing_score > 0
                else 0.0
            )

            result["aligned_score"] = aligned_score
            result["offset_score"] = offset_score
            result["timing_score_normalized"] = timing_score
            result["final_score"] = (
                0.45 * aligned_score
                + 0.25 * offset_score
                + 0.20 * result["hash_coverage"]
                + 0.10 * timing_score
            )

        results.sort(
            key=lambda result: (
                result["final_score"],
                result["aligned_matches"],
                result["dominant_offset_count"],
                result["timing_score"],
                result["matched_hashes"],
                result["weighted_hash_matches"],
                result["hash_matches"],
            ),
            reverse=True,
        )

        for result in results:
            cursor.execute(
                """
                SELECT songName
                FROM SONG_DATA
                WHERE songID = ?
                """,
                (result["song_id"],),
            )
            row = cursor.fetchone()
            result["song_name"] = row[0] if row else None
            result["first_match_seconds"] = result["first_match_frame"] * 512 / 11025

        print(results)
        return results[:3]
    finally:
        conn.close()


if __name__ == "__main__":
    print(match_song("./untitled.wav"))