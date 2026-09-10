from main import Process_audio
import sqlite3
from collections import defaultdict


def match_song(audio_file="./untitled.wav"):
    # ============================================
    # PROCESS QUERY AUDIO
    # ============================================

    process = Process_audio(audio_file)

    signal = process.convert_stereo_to_mono()
    waveform = process.low_pass_filter_tensor()
    resampled_filename = process.resample()

    spectogram, peaks = process.caclulate_spectogram(
        resampled_filename
    )

    query_hashes = {}

    process.calculate_hashes(
        peaks,
        5,
        "query",
        query_hashes
    )

    # ============================================
    # CONNECT TO DATABASE
    # ============================================

    conn = sqlite3.connect("example.db")
    cursor = conn.cursor()

    try:
        # ============================================
        # STEP 1:
        # FIND ACTUAL HASH MATCHES
        # ============================================

        matched_pairs_by_song = defaultdict(list)
        hash_matches_by_song = defaultdict(int)

        for hash_id, query_points in query_hashes.items():

            cursor.execute(
                """
                SELECT time, song_id
                FROM FINGERPRINT
                WHERE hash = ?
                """,
                (hash_id,)
            )

            db_matches = cursor.fetchall()

            if not db_matches:
                continue

            for query_time, _ in query_points:

                for db_time, song_id in db_matches:

                    matched_pairs_by_song[song_id].append(
                        (query_time, db_time)
                    )

                    hash_matches_by_song[song_id] += 1

        # ============================================
        # STEP 2:
        # TOP 3 BY RAW HASH MATCHES
        # ============================================

        top_3_songs = sorted(
            hash_matches_by_song.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # ============================================
        # SCORING PARAMETERS
        # ============================================

        THRESHOLD = 100
        OFFSET_TOLERANCE = 5

        # ============================================
        # STEP 3:
        # TEMPORAL ANALYSIS FOR TOP 3
        # ============================================

        results = []

        for song_id, hash_match_count in top_3_songs:

            pairs = matched_pairs_by_song[song_id]
            pairs = list(set(pairs))

            # Find dominant offset
            offset_counts = defaultdict(int)

            for query_time, db_time in pairs:
                offset = db_time - query_time
                offset_counts[offset] += 1

            if not offset_counts:
                results.append({
                    "song_id": song_id,
                    "hash_matches": hash_match_count,
                    "aligned_matches": 0,
                    "timing_score": 0,
                    "dominant_offset": 0,
                    "dominant_offset_count": 0,
                    "first_match_frame": 0,
                })
                continue

            dominant_offset, dominant_offset_count = max(
                offset_counts.items(),
                key=lambda x: x[1]
            )

            # Keep only matches near dominant offset
            aligned_pairs = []

            for query_time, db_time in pairs:
                offset = db_time - query_time

                if abs(offset - dominant_offset) <= OFFSET_TOLERANCE:
                    aligned_pairs.append((query_time, db_time))

            aligned_pairs = sorted(
                set(aligned_pairs),
                key=lambda p: p[0]
            )

            aligned_matches = len(aligned_pairs)

            # Successive timing check
            timing_score = 0
            first_match_frame = None

            for i in range(len(aligned_pairs) - 1):

                query_time_1, db_time_1 = aligned_pairs[i]
                query_time_2, db_time_2 = aligned_pairs[i + 1]

                query_diff = abs(
                    query_time_2 - query_time_1
                )

                db_diff = abs(
                    db_time_2 - db_time_1
                )

                diff_of_diffs = abs(
                    db_diff - query_diff
                )

                if diff_of_diffs < THRESHOLD:
                    timing_score += 1

                    if first_match_frame is None:
                        first_match_frame = db_time_1

            if first_match_frame is None:
                if aligned_pairs:
                    first_match_frame = aligned_pairs[0][1]
                else:
                    first_match_frame = 0

            results.append({
                "song_id": song_id,
                "hash_matches": hash_match_count,
                "aligned_matches": aligned_matches,
                "timing_score": timing_score,
                "dominant_offset": dominant_offset,
                "dominant_offset_count": dominant_offset_count,
                "first_match_frame": first_match_frame,
            })

        # ============================================
        # STEP 4:
        # NORMALIZE THE THREE FACTORS
        # ============================================

        if not results:
            return []

        max_hash_matches = max(
            result["hash_matches"]
            for result in results
        )

        max_aligned_matches = max(
            result["aligned_matches"]
            for result in results
        )

        max_timing_score = max(
            result["timing_score"]
            for result in results
        )

        HASH_WEIGHT = 0.30
        ALIGNMENT_WEIGHT = 0.35
        TIMING_WEIGHT = 0.35

        for result in results:

            hash_score = (
                result["hash_matches"] / max_hash_matches
                if max_hash_matches > 0
                else 0.0
            )

            alignment_score = (
                result["aligned_matches"] / max_aligned_matches
                if max_aligned_matches > 0
                else 0.0
            )

            timing_score_normalized = (
                result["timing_score"] / max_timing_score
                if max_timing_score > 0
                else 0.0
            )

            result["hash_score"] = hash_score
            result["alignment_score"] = alignment_score
            result["timing_score_normalized"] = timing_score_normalized

            result["final_score"] = (
                HASH_WEIGHT * hash_score
                + ALIGNMENT_WEIGHT * alignment_score
                + TIMING_WEIGHT * timing_score_normalized
            )

        # ============================================
        # STEP 5:
        # RANK BY FINAL SCORE
        # ============================================

        results.sort(
            key=lambda x: x["final_score"],
            reverse=True
        )

        # ============================================
        # ADD SONG METADATA
        # ============================================

        for result in results:

            cursor.execute(
                """
                SELECT songName
                FROM SONG_DATA
                WHERE songID = ?
                """,
                (result["song_id"],)
            )

            row = cursor.fetchone()
            result["song_name"] = row[0] if row else None

            result["first_match_seconds"] = (
                result["first_match_frame"] * 512 / 11025
            )

        # ============================================
        # RETURN RANKED MATCH DATA
        # ============================================

        return results

    finally:
        conn.close()


if __name__ == "__main__":
    song_ids = match_song("./untitled.wav")
    print(song_ids)
