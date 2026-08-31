#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import av
import cv2
import numpy as np


def _sine(t: np.ndarray, freq: float, phase: float = 0.0) -> np.ndarray:
    return np.sin(2 * np.pi * freq * t + phase)


def _env_pulse(t: np.ndarray, starts: np.ndarray, decay: float) -> np.ndarray:
    y = np.zeros_like(t)
    for start in starts:
        idx = t >= start
        x = t[idx] - start
        y[idx] += np.exp(-x / decay)
    return y


def make_track(duration: float, sample_rate: int, fade_start: float) -> np.ndarray:
    n = int(sample_rate * duration)
    t = np.arange(n, dtype=np.float32) / sample_rate
    bpm = 128.0
    beat = 60.0 / bpm
    beats = np.arange(0, duration + beat, beat)
    half_beats = np.arange(0, duration + beat / 2, beat / 2)

    kick = np.zeros_like(t)
    for b in beats:
        x = t - b
        m = (x >= 0) & (x < 0.16)
        freq = 82 * np.exp(-x[m] * 17) + 38
        kick[m] += np.sin(2 * np.pi * freq * x[m]) * np.exp(-x[m] * 18)

    rng = np.random.default_rng(830)
    noise = rng.normal(0, 1, n).astype(np.float32)

    clap = np.zeros_like(t)
    for b in beats[1::2]:
        x = t - b
        m = (x >= 0) & (x < 0.10)
        clap[m] += noise[m] * np.exp(-x[m] * 28)

    hat = np.zeros_like(t)
    for b in half_beats:
        x = t - b
        m = (x >= 0) & (x < 0.045)
        hat[m] += noise[m] * np.exp(-x[m] * 75)

    duck = 1.0 - 0.24 * np.clip(_env_pulse(t, beats, 0.11), 0, 1)
    notes = [523.25, 659.25, 783.99, 659.25, 587.33, 739.99, 880.00, 739.99]
    pluck = np.zeros_like(t)
    for i, b in enumerate(np.arange(0, duration, beat / 2)):
        freq = notes[i % len(notes)]
        x = t - b
        m = (x >= 0) & (x < 0.30)
        tone = 0.65 * _sine(t, freq)[m] + 0.25 * _sine(t, freq * 2.0)[m]
        pluck[m] += tone * np.exp(-x[m] * 11)

    chord = 0.35 * _sine(t, 261.63) + 0.25 * _sine(t, 329.63) + 0.22 * _sine(t, 392.00)
    pad_env = np.clip((t - 0.35) / 1.2, 0, 1)
    pad = chord * pad_env

    riser_env = np.clip((t - 5.4) / 1.0, 0, 1) * np.clip((8.4 - t) / 1.2, 0, 1)
    riser = _sine(t, 1046.5 + 190 * np.sin(2 * np.pi * 0.18 * t)) * riser_env * 0.08

    music = 0.50 * kick + 0.16 * clap + 0.055 * hat + 0.22 * pluck * duck + 0.11 * pad * duck + riser
    intro = np.clip(t / 0.35, 0, 1)
    section = 0.78 + 0.22 * np.clip((t - 5.8) / 1.2, 0, 1)

    fade = np.ones_like(t)
    idx = t >= fade_start
    x = np.clip((t[idx] - fade_start) / max(0.001, duration - fade_start), 0, 1)
    fade[idx] = 0.5 * (1.0 + np.cos(np.pi * x))

    music *= intro * section * fade
    left = music + 0.035 * _sine(t, 523.25, 0.7) * np.clip((t - 5.8) / 1.0, 0, 1) * fade
    right = music + 0.035 * _sine(t, 783.99, 1.9) * np.clip((t - 5.8) / 1.0, 0, 1) * fade
    stereo = np.vstack([left, right])
    peak = np.max(np.abs(stereo)) or 1.0
    return np.clip(stereo / peak * 0.42 * 32767, -32768, 32767).astype(np.int16)


def mux_music(src: Path, out: Path, fade_start: float) -> None:
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {src}")
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_float = cap.get(cv2.CAP_PROP_FPS)
    duration = frames / fps_float

    sample_rate = 48000
    pcm = make_track(duration, sample_rate, fade_start)

    in_container = av.open(str(src), mode="r")
    in_video = in_container.streams.video[0]
    fps = in_video.average_rate
    width = in_video.codec_context.width
    height = in_video.codec_context.height

    out.parent.mkdir(parents=True, exist_ok=True)
    out_container = av.open(str(out), mode="w")
    vstream = out_container.add_stream("h264", rate=fps)
    vstream.width = width
    vstream.height = height
    vstream.pix_fmt = "yuv420p"
    vstream.options = {"crf": "23", "preset": "medium"}

    astream = out_container.add_stream("aac", rate=sample_rate)
    astream.layout = "stereo"
    astream.bit_rate = 128000

    for frame in in_container.decode(video=0):
        for packet in vstream.encode(frame):
            out_container.mux(packet)
    for packet in vstream.encode(None):
        out_container.mux(packet)

    pts = 0
    for start in range(0, pcm.shape[1], 1024):
        block = pcm[:, start:start + 1024]
        frame = av.AudioFrame.from_ndarray(block, format="s16p", layout="stereo")
        frame.sample_rate = sample_rate
        frame.pts = pts
        pts += frame.samples
        for packet in astream.encode(frame):
            out_container.mux(packet)
    for packet in astream.encode(None):
        out_container.mux(packet)

    out_container.close()
    in_container.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Add original TikTok-style music with ending fadeout.")
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fade-start", type=float, default=8.0)
    args = parser.parse_args()
    mux_music(args.video, args.out, args.fade_start)
    print(f"OUTPUT={args.out}")


if __name__ == "__main__":
    main()
