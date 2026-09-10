import { useRef, useState } from "react";
import { uploadWavBlob } from "./fetchSong";
export default function AudioRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);

  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
    });

    const audioContext = new AudioContext();

    const source =
      audioContext.createMediaStreamSource(stream);

    const processor =
      audioContext.createScriptProcessor(4096, 1, 1);

    chunksRef.current = [];

    processor.onaudioprocess = (event) => {
      const samples =
        event.inputBuffer.getChannelData(0);

      chunksRef.current.push(
        new Float32Array(samples)
      );
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    streamRef.current = stream;
    audioContextRef.current = audioContext;
    sourceRef.current = source;
    processorRef.current = processor;

    setIsRecording(true);
  };

  const stopRecording = async () => {
    setIsRecording(false);

    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();

    streamRef.current?.getTracks().forEach((track) =>
      track.stop()
    );

    const sampleRate =
      audioContextRef.current.sampleRate;

    const wavBlob = createWavBlob(
      chunksRef.current,
      sampleRate
    );

    const url = URL.createObjectURL(wavBlob);

    setAudioUrl(url);

    await audioContextRef.current.close();
    let response = await uploadWavBlob(wavBlob);
    console.log(response)

  };

  return (
    <div>
      <button
        onClick={
          isRecording
            ? stopRecording
            : startRecording
        }
      >
        {isRecording
          ? "Stop Recording"
          : "Start Recording"}
      </button>

      {audioUrl && (
        <div style={{ marginTop: 16 }}>
          <audio controls src={audioUrl} />
          <br />
          <a
            href={audioUrl}
            download="recording.wav"
          >
            Download WAV
          </a>
        </div>
      )}
    </div>
  );
}

function createWavBlob(chunks, sampleRate) {
  const samples = mergeChunks(chunks);

  const buffer = new ArrayBuffer(
    44 + samples.length * 2
  );

  const view = new DataView(buffer);

  writeString(view, 0, "RIFF");
  view.setUint32(
    4,
    36 + samples.length * 2,
    true
  );

  writeString(view, 8, "WAVE");

  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);

  writeString(view, 36, "data");
  view.setUint32(
    40,
    samples.length * 2,
    true
  );

  let offset = 44;

  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(
      -1,
      Math.min(1, samples[i])
    );

    view.setInt16(
      offset,
      s < 0 ? s * 32768 : s * 32767,
      true
    );

    offset += 2;
  }

  return new Blob([buffer], {
    type: "audio/wav",
  });
}

function mergeChunks(chunks) {
  let totalLength = 0;

  chunks.forEach((chunk) => {
    totalLength += chunk.length;
  });

  const result = new Float32Array(totalLength);

  let offset = 0;

  chunks.forEach((chunk) => {
    result.set(chunk, offset);
    offset += chunk.length;
  });

  return result;
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(
      offset + i,
      str.charCodeAt(i)
    );
  }
}