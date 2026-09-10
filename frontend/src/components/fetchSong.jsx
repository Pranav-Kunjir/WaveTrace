import axios from "axios";

export async function uploadWavBlob(wavBlob) {
  const formData = new FormData();

  formData.append(
    "file",
    wavBlob,
    "recording.wav"
  );

  const response = await axios.post(
    "http://localhost:8000/upload-audio",
    formData
  );

  return response.data;
}