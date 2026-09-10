from fastapi import FastAPI, File, UploadFile
import os
from check_song import match_song
from fastapi.middleware.cors import CORSMiddleware
import uuid
import asyncio
import sqlite3
from pathlib import Path
app = FastAPI()

DATABASE_PATH = Path(__file__).resolve().parent / "example.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
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
    # 1. Access file metadata
    filename = file.filename
    content_type = file.content_type
    
    # 2. Read the audio content as bytes
    audio_bytes = await file.read()
    
    # Example: Optional step to save the file locally
    save_path = Path(__file__).resolve().parent / f"saved_{uuid.uuid4()}.wav"
    with open(save_path, "wb") as f:
        f.write(audio_bytes)

    song_ids = await asyncio.to_thread(match_song, str(save_path))
    paths = [save_path, save_path.with_name(f"resampled-{save_path.name}")]
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
    idx += 1
    return song_ids

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}