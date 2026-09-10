from fastapi import FastAPI, File, UploadFile
import os
from check_song import match_song
app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}
@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    # 1. Access file metadata
    filename = file.filename
    content_type = file.content_type
    
    # 2. Read the audio content as bytes
    audio_bytes = await file.read()
    
    # Example: Optional step to save the file locally
    save_path = f"saved_{filename}"
    with open(save_path, "wb") as f:
        f.write(audio_bytes)
    song_ids = match_song(save_path)
    return song_ids

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}