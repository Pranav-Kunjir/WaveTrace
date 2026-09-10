"""Create database fingerprints for WAV files in backend/songs."""

import argparse
import sqlite3
from pathlib import Path

from main import Process_audio


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_SONGS_DIR = BACKEND_DIR / "songs"
DEFAULT_DATABASE = BACKEND_DIR / "example.db"


def ensure_schema(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS SONG_DATA (
            songID INTEGER PRIMARY KEY,
            songName VARCHAR(250) NOT NULL UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS FINGERPRINT (
            hash INTEGER NOT NULL,
            time INTEGER NOT NULL,
            song_id INTEGER NOT NULL
        )
        """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_fingerprint_hash ON FINGERPRINT(hash)"
    )


def get_next_song_id(cursor):
    cursor.execute("SELECT COALESCE(MAX(songID), -1) + 1 FROM SONG_DATA")
    return cursor.fetchone()[0]


def fingerprint_song(song_path, song_id):
    process = Process_audio(str(song_path))
    process.convert_stereo_to_mono()
    process.low_pass_filter_tensor()
    resampled_path = Path(process.resample())

    try:
        _, peaks = process.caclulate_spectogram(str(resampled_path))
        fingerprints = {}
        process.calculate_hashes(peaks, 5, song_id, fingerprints)
        rows = [
            (hash_id, frame, song_id)
            for hash_id, points in fingerprints.items()
            for frame, _ in points
        ]
        return rows
    finally:
        resampled_path.unlink(missing_ok=True)


def ingest(songs_dir=DEFAULT_SONGS_DIR, database=DEFAULT_DATABASE):
    songs_dir = Path(songs_dir)
    song_paths = sorted(
        path
        for path in songs_dir.glob("*.wav")
        if not path.name.startswith("resampled-")
    )

    if not song_paths:
        print(f"No WAV files found in {songs_dir}")
        return

    conn = sqlite3.connect(database)
    cursor = conn.cursor()

    try:
        ensure_schema(cursor)
        conn.commit()
        next_song_id = get_next_song_id(cursor)
        inserted = 0

        for song_path in song_paths:
            song_name = song_path.stem
            cursor.execute(
                "SELECT songID FROM SONG_DATA WHERE songName = ?",
                (song_name,),
            )
            if cursor.fetchone() is not None:
                print(f"Skipping existing song: {song_name}")
                continue

            print(f"Fingerprinting [{next_song_id}] {song_name}")
            fingerprint_rows = fingerprint_song(song_path, next_song_id)
            if not fingerprint_rows:
                print(f"Skipping empty fingerprint set: {song_name}")
                continue

            cursor.execute(
                "INSERT INTO SONG_DATA (songID, songName) VALUES (?, ?)",
                (next_song_id, song_name),
            )
            cursor.executemany(
                "INSERT INTO FINGERPRINT (hash, time, song_id) VALUES (?, ?, ?)",
                fingerprint_rows,
            )
            conn.commit()
            print(f"Added {len(fingerprint_rows)} fingerprints")
            next_song_id += 1
            inserted += 1

        print(f"Ingestion complete: {inserted} new song(s)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate fingerprints and add WAV songs to the database."
    )
    parser.add_argument("--songs-dir", type=Path, default=DEFAULT_SONGS_DIR)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing song metadata and fingerprints before ingestion",
    )
    args = parser.parse_args()

    if args.reset and args.database.exists():
        args.database.unlink()

    ingest(args.songs_dir, args.database)


if __name__ == "__main__":
    main()
