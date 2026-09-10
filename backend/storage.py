import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent


def get_data_dir():
    configured_dir = Path(os.getenv("WAVETRACE_DATA_DIR", BACKEND_DIR))

    try:
        configured_dir.mkdir(parents=True, exist_ok=True)
        test_file = configured_dir / ".write-test"
        test_file.touch()
        test_file.unlink()
        return configured_dir
    except OSError:
        fallback_dir = Path("/tmp/wavetrace-data")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        print(
            f"Warning: {configured_dir} is not writable; using {fallback_dir}. "
            "Attach the Render persistent disk at WAVETRACE_DATA_DIR to persist data."
        )
        return fallback_dir


DATA_DIR = get_data_dir()
DATABASE_PATH = DATA_DIR / "example.db"