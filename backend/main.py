import hashlib
from pathlib import Path

import torch
import scipy
import torchaudio 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import librosa
import librosa.display
import torchaudio
from scipy import signal
from scipy.io import wavfile
import torchaudio.functional as F


class Process_audio:
    def __init__(self,filename):
        self.filename = filename
        self.waveform, self.sr = torchaudio.load(filename)
        self.resampled_filename = ""
        

    def convert_stereo_to_mono(self):
        if self.waveform.shape[0] > 1:
            self.waveform = torch.mean(self.waveform,dim=0,keepdim=True)
        return self.waveform
    def low_pass_filter_tensor(self,cutoff=5000):
        self.waveform = torchaudio.functional.lowpass_biquad(self.waveform,self.sr,cutoff)
        return self.waveform
    def resample(self):
        resample_rate = 11025 
        resampled_waveform = F.resample(
            self.waveform,
            self.sr,
            resample_rate,
            lowpass_filter_width=16,
            rolloff=0.85,
            resampling_method="sinc_interp_kaiser",
            beta=8.555504641634386,
        )
        source_path = Path(self.filename)
        output_path = source_path.with_name(f"resampled-{source_path.name}")
        torchaudio.save(str(output_path), resampled_waveform, resample_rate)
        self.resampled_filename = str(output_path)
        return self.resampled_filename

    def visualize_data(self,audiofiles):
        i = 1
        for file in audiofiles:
            y, sr = librosa.load(file, sr=None)
            #plt.figure(figsize=(10,7))
            #librosa.display.waveshow(y, sr=sr)
            #plt.title(f"Waveform {file}")
            #plt.xlabel("Time (s)")
            #plt.ylabel("Amplitude")
            #plt.show()

            spectrogram = librosa.amplitude_to_db(librosa.stft(y), ref=np.max)
            plt.figure(figsize=(10, 4))
            librosa.display.specshow(spectrogram, sr=sr, x_axis='time', y_axis='log')
            plt.colorbar(format='%+2.0f dB')
            plt.title("🎛️ Spectrogram")
            plt.show()
    
    def caclulate_spectogram(self,file):
        peaks = []
        sample_rate, samples = wavfile.read(file)
        window_size = 1024
        hop_size = 512
        window = np.hanning(window_size)
        spectrogram_list = []
        total_samples = len(samples)
        frame_idx = 0
        
        for i in range(0, total_samples- window_size, hop_size):

            chunk = samples[i : i + window_size]
            window_chunk =  chunk * window
            fft_result = np.fft.rfft(window_chunk)

            fft_result = np.abs(fft_result)
            very_low_sound_band = (0,10,  np.max(fft_result[0:10])    ,np.argmax(fft_result[0:10])    )
            low_sound_band =      (10,20, np.max(fft_result[10:20])   ,np.argmax(fft_result[10:20]) +10  )
            low_mid_sound_band =  (20,40, np.max(fft_result[20:40])   ,np.argmax(fft_result[20:40]) +20  )
            mid_sound_band =      (40,80, np.max(fft_result[40:80])   ,np.argmax(fft_result[40:80]) +40  )
            mid_high_sound_band = (80,160,np.max(fft_result[80:160])  ,np.argmax(fft_result[80:160])+80  )
            high_sound_band =     (160,513,np.max(fft_result[160:512]),np.argmax(fft_result[160:512])+160)
            arrr = [very_low_sound_band,low_sound_band,low_mid_sound_band,mid_sound_band,mid_high_sound_band,high_sound_band]
            mean = 0
            for band in arrr:
                mean += band[2]
            mean /= 6
            for band in arrr:
                if band[2] < mean:
                    fft_result[band[0]:band[1]] = 0
                else:
                    fft_result[band[0]:band[3]] = 0
                    fft_result[band[3]+1:band[1]] = 0
                    fft_result[band[3]] *= 1000
                    peaks.append((frame_idx,band[3],fft_result[band[3]]))
            #list appending 
            spectrogram_list.append(fft_result)
            frame_idx += 1
        spectrogram = np.array(spectrogram_list).T
        # print(spectrogram.shape)

        # Add a tiny value (1e-10) to avoid log(0) errors

        # spectrogram_db = 10 * np.log10(spectrogram + 1e-10)

        
        # 5. Define Time and Frequency Axes for plotting
        # total_duration = total_samples / sample_rate
        # num_freq_bins = spectrogram.shape[0]
        # max_frequency = sample_rate / 2  # Nyquist frequency
        
        # # 6. Plot the manual FFT Spectrogram
        # plt.figure(figsize=(10, 4))
        # plt.imshow(
        #     spectrogram_db,
        #     origin="lower",
        #     aspect="auto",
        #     cmap="inferno",
        #     extent=[0, total_duration, 0, max_frequency],
        # )
        
        # plt.title("Manual FFT Spectrogram (From Scratch)")
        # plt.xlabel("Time (seconds)")
        # plt.ylabel("Frequency (Hz)")
        # plt.colorbar(label="Intensity (dB)")
        # plt.tight_layout()
        # plt.show()
        return spectrogram, peaks

    def calculate_hashes(self,peaks, target_zone,song_id,hashtable):
        for i in range(0,len(peaks)-target_zone):
            for j in range(1,target_zone):
                point = (peaks[i][1],peaks[i+j][1],peaks[i+j][0]-peaks[i][0])
                hash_id = int.from_bytes(
                    hashlib.blake2b(
                        repr(point).encode("ascii"),
                        digest_size=8,
                    ).digest(),
                    "big",
                    signed=True,
                )
                hashtable.setdefault(hash_id, []).append((peaks[i][0], song_id))




