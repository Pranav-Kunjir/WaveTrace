from fastapi import FastAPI, File, HTTPException, UploadFile
import os
import shutil
from check_song import match_song
from fastapi.middleware.cors import CORSMiddleware
import uuid
import asyncio
import sqlite3
from pathlib import Path
from os import getenv
from storage import DATA_DIR, DATABASE_PATH
app = FastAPI()

BUNDLED_DATABASE_PATH = Path(__file__).resolve().parent / "example.db"

if not DATABASE_PATH.exists() and BUNDLED_DATABASE_PATH.exists():
    shutil.copy2(BUNDLED_DATABASE_PATH, DATABASE_PATH)

configured_origins = getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in configured_origins.split(",")
    if origin.strip()
]
if "http://localhost:5173" not in allowed_origins:
    allowed_origins.append("http://localhost:5173")
if "https://wave-trace.vercel.app" not in allowed_origins:
    allowed_origins.append("https://wave-trace.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

idx = 0

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/songs")
def get_songs():
    with sqlite3.connect(DATABASE_PATH) as connection:
        rows = connection.execute(
            "SELECT songID, songName FROM SONG_DATA ORDER BY songID"
        ).fetchall()

    return {
        "total": len(rows),
        "songs": [
            {"song_id": song_id, "song_name": song_name}
            for song_id, song_name in rows
        ],
    }

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    global idx
    audio_bytes = await file.read()
    save_path = DATA_DIR / f"saved_{uuid.uuid4()}.wav"
    resampled_path = save_path.with_name(f"resampled-{save_path.name}")

    try:
        save_path.write_bytes(audio_bytes)
        song_ids = await asyncio.to_thread(match_song, str(save_path))
        idx += 1
        return song_ids
    except Exception as error:
        print(f"Audio matching failed: {error}")
        raise HTTPException(
            status_code=500,
            detail="Audio processing failed. Check the backend logs for details.",
        ) from error
    finally:
        for path in (save_path, resampled_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}