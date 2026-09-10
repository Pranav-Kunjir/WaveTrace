import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function uploadWavBlob(wavBlob) {
  const formData = new FormData();

  formData.append(
    "file",
    wavBlob,
    "recording.wav"
  );

  const response = await axios.post(
    `${API_BASE_URL}/upload-audio`,
    formData
  );

  return response.data;
}

export async function fetchSongs() {
  const response = await axios.get(`${API_BASE_URL}/songs`);
  return response.data;
}