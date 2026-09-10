import { useEffect, useRef, useState } from "react";
import { uploadWavBlob } from "./fetchSong";

const RECORDING_DURATION = 12;

export default function AudioRecorder({ onResult, onStatusChange, onError }) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(RECORDING_DURATION);

  const audioContextRef = useRef(null);
  const streamRef = useRef(null);
  const sourceRef = useRef(null);
  const processorRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  const stoppingRef = useRef(false);

  useEffect(() => () => {
    clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((track) => track.stop());
    audioContextRef.current?.close();
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
      const audioContext = new AudioContext();

      const source = audioContext.createMediaStreamSource(stream);

      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      chunksRef.current = [];
      stoppingRef.current = false;

      processor.onaudioprocess = (event) => {
        const samples = event.inputBuffer.getChannelData(0);

        chunksRef.current.push(new Float32Array(samples));
      };

      source.connect(processor);
      const silentOutput = audioContext.createGain();
      silentOutput.gain.value = 0;
      processor.connect(silentOutput);
      silentOutput.connect(audioContext.destination);

      streamRef.current = stream;
      audioContextRef.current = audioContext;
      sourceRef.current = source;
      processorRef.current = processor;

      setSecondsLeft(RECORDING_DURATION);
      setIsRecording(true);
      onStatusChange?.('recording');
      timerRef.current = setInterval(() => {
        setSecondsLeft((current) => {
          if (current <= 1) {
            stopRecording();
            return 0;
          }
          return current - 1;
        });
      }, 1000);
    } catch {
      onError?.('Microphone access is needed to identify a song.');
    }
  };

  const stopRecording = async () => {
    if (stoppingRef.current || !audioContextRef.current) return;
    stoppingRef.current = true;
    clearInterval(timerRef.current);
    setIsRecording(false);
    onStatusChange?.('processing');

    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();

    streamRef.current?.getTracks().forEach((track) =>
      track.stop()
    );

    const sampleRate = audioContextRef.current.sampleRate;

    const wavBlob = createWavBlob(
      chunksRef.current,
      sampleRate
    );

    await audioContextRef.current.close();
    try {
      const response = await uploadWavBlob(wavBlob);
      onResult?.(response);
    } catch {
      onError?.('The song could not be identified. Check that the API is running and try again.');
    } finally {
      audioContextRef.current = null;
      setIsProcessing(false);
      stoppingRef.current = false;
    }
  };

  return (
    <div className="recorder">
      <button className={`listen-button ${isRecording ? 'is-recording' : ''}`} onClick={isRecording ? stopRecording : startRecording} disabled={isRecording || isProcessing}>
        <span className="listen-ring">
          <svg className="mic-icon" viewBox="0 0 24 28" aria-hidden="true" focusable="false">
            <rect x="7" y="2" width="10" height="17" rx="5" />
            <path d="M3 14a9 9 0 0 0 18 0M12 23v3M8 26h8" />
          </svg>
        </span>
        <span>{isRecording ? 'Listening...' : isProcessing ? 'Finding your song...' : 'Tap to identify'}</span>
      </button>
      <div className="recording-status" aria-live="polite">{isRecording ? <><span className="pulse-dot" /> Listening for <strong>{secondsLeft}s</strong></> : isProcessing ? 'Matching your recording' : 'Ready when you are'}</div>
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