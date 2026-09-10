"""Download YouTube audio and convert it to WAV files for fingerprinting."""

import argparse
import re
import shutil
import subprocess
from pathlib import Path

import yt_dlp


BACKEND_DIR = Path(__file__).resolve().parent
SONGS_DIR = BACKEND_DIR / "songs"


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", value).strip()
    return re.sub(r"\s+", " ", value) or "untitled"


def download_and_convert(url, keep_mp3=False, overwrite=False):
    SONGS_DIR.mkdir(parents=True, exist_ok=True)

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(SONGS_DIR / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "overwrites": overwrite,
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=True)

    video_id = info["id"]
    title = safe_name(info.get("title", video_id))
    mp3_path = SONGS_DIR / f"{video_id}.mp3"
    wav_path = SONGS_DIR / f"{title} [{video_id}].wav"

    if not mp3_path.exists():
        raise FileNotFoundError(f"yt-dlp did not create the expected MP3: {mp3_path}")

    if wav_path.exists() and not overwrite:
        print(f"Skipping existing file: {wav_path.name}")
    else:
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y" if overwrite else "-n",
            "-i",
            str(mp3_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            str(wav_path),
        ]
        subprocess.run(command, check=True)
        print(f"Created: {wav_path.name}")

    if not keep_mp3:
        mp3_path.unlink(missing_ok=True)

    return wav_path


def read_urls(url_file):
    if not url_file:
        return []

    with Path(url_file).open(encoding="utf-8") as file:
        return [
            line.strip()
            for line in file
            if line.strip() and not line.lstrip().startswith("#")
        ]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download YouTube audio and convert it to WAV files."
    )
    parser.add_argument("urls", nargs="*", help="YouTube video URLs")
    parser.add_argument(
        "--url-file",
        type=Path,
        help="Text file containing one YouTube URL per line",
    )
    parser.add_argument(
        "--keep-mp3",
        action="store_true",
        help="Keep the intermediate MP3 files",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing downloaded audio and WAV files",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    urls = args.urls + read_urls(args.url_file)

    if not urls:
        raise SystemExit("Provide YouTube URLs or use --url-file.")

    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required and must be available on PATH.")

    for url in urls:
        try:
            download_and_convert(
                url,
                keep_mp3=args.keep_mp3,
                overwrite=args.overwrite,
            )
        except Exception as error:
            print(f"Failed: {url}\n  {error}")


if __name__ == "__main__":
    main()