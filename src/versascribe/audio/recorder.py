"""AudioRecorder: captures system audio via BlackHole into a WAV file."""

from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from typing import Optional


class AudioRecorder:
    """Thread-safe audio recorder using sounddevice + soundfile.

    Audio callback is non-blocking (put_nowait). A separate writer thread
    drains the queue and writes to a WAV file. After stop(), the writer
    thread fully drains the queue before closing the file.
    """

    SAMPLE_RATE = 16000
    BLOCK_SIZE = 4096  # ~256 ms chunks

    def __init__(self, wav_path: Path, device: int | str) -> None:
        self._wav_path = wav_path
        self._device = device
        self._input_channels: int = 1
        self._q: queue.Queue = queue.Queue(maxsize=512)
        self._stop_event = threading.Event()
        self._peak: float = 0.0
        self._start_time: float = 0.0
        self._writer_thread: Optional[threading.Thread] = None
        self._stream = None
        self._dropped_frames: int = 0

    @property
    def wav_path(self) -> Path:
        return self._wav_path

    def get_peak_level(self) -> float:
        return self._peak

    def get_elapsed(self) -> str:
        if not self._start_time:
            return "00:00"
        elapsed = int(time.time() - self._start_time)
        m, s = divmod(elapsed, 60)
        return f"{m:02d}:{s:02d}"

    def start(self) -> None:
        import sounddevice as sd

        device_info = sd.query_devices(self._device, "input")
        self._input_channels = max(1, int(device_info["max_input_channels"]))

        self._writer_thread = threading.Thread(
            target=self._writer_worker, daemon=True
        )
        self._writer_thread.start()

        self._stream = sd.InputStream(
            device=self._device,
            samplerate=self.SAMPLE_RATE,
            channels=self._input_channels,
            dtype="float32",
            blocksize=self.BLOCK_SIZE,
            callback=self._audio_callback,
        )
        self._start_time = time.time()
        self._stream.start()

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._stop_event.set()

    def wait(self) -> None:
        if self._writer_thread:
            self._writer_thread.join()

    def _audio_callback(self, indata, frames, time_info, status) -> None:
        import numpy as np

        # Mix all input channels to mono so Aggregate Devices (mic + BlackHole)
        # are captured correctly regardless of channel count.
        if indata.shape[1] > 1:
            frame = np.mean(indata, axis=1, keepdims=True)
        else:
            frame = indata.copy()
        self._peak = float(np.max(np.abs(frame)))
        try:
            self._q.put_nowait(frame)
        except queue.Full:
            self._dropped_frames += 1

    def _writer_worker(self) -> None:
        import soundfile as sf

        with sf.SoundFile(
            str(self._wav_path),
            mode="w",
            samplerate=self.SAMPLE_RATE,
            channels=1,
            subtype="PCM_16",
        ) as f:
            while not self._stop_event.is_set() or not self._q.empty():
                try:
                    frame = self._q.get(timeout=0.5)
                    f.write(frame)
                except queue.Empty:
                    continue
            f.flush()
