import argparse
import os
import sys
from typing import List, Tuple

import numpy as np

try:
    import librosa
except Exception as e:
    print("需要安装依赖库: librosa", file=sys.stderr)
    raise

try:
    import pretty_midi
except Exception as e:
    print("需要安装依赖库: pretty_midi", file=sys.stderr)
    raise


def load_audio(path: str, sr: int) -> Tuple[np.ndarray, int]:
    y, sr_ret = librosa.load(path, sr=sr, mono=True)
    return y, sr_ret


def estimate_notes(
    y: np.ndarray,
    sr: int,
    min_midi: int,
    max_midi: int,
    fps: int,
) -> List[Tuple[int, float, float, int]]:
    hop_length = max(32, int(sr // max(1, fps)))
    fmin = librosa.midi_to_hz(min_midi)
    fmax = librosa.midi_to_hz(max_midi)
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length
    )
    times = librosa.frames_to_time(np.arange(len(f0)), sr=sr, hop_length=hop_length)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
    onset_env = onset_env.astype(np.float32)
    max_env = float(np.max(onset_env)) if onset_env.size else 1.0
    notes: List[Tuple[int, float, float, int]] = []
    i = 0
    n = len(f0)
    while i < n:
        if voiced_flag[i]:
            start = i
            while i < n and voiced_flag[i]:
                i += 1
            end = i
            seg = f0[start:end]
            pitch_hz = float(np.nanmedian(seg)) if seg.size else np.nan
            if np.isnan(pitch_hz):
                continue
            midi_pitch = int(np.round(librosa.hz_to_midi(pitch_hz)))
            midi_pitch = int(np.clip(midi_pitch, min_midi, max_midi))
            env_val = float(onset_env[start]) if start < len(onset_env) else 0.0
            velocity = int(np.clip((env_val / (max_env + 1e-6)) * 100.0 + 20.0, 1, 127))
            start_t = float(times[start])
            end_idx = min(end, len(times) - 1)
            end_t = float(times[end_idx])
            if end_t <= start_t:
                end_t = start_t + (hop_length / sr)
            notes.append((midi_pitch, start_t, end_t, velocity))
        else:
            i += 1
    return notes


def write_midi(notes: List[Tuple[int, float, float, int]], instrument_program: int, output_path: str) -> None:
    pm = pretty_midi.PrettyMIDI()
    instrument = pretty_midi.Instrument(program=int(instrument_program))
    for pitch, start_t, end_t, velocity in notes:
        instrument.notes.append(
            pretty_midi.Note(velocity=int(velocity), pitch=int(pitch), start=float(start_t), end=float(end_t))
        )
    pm.instruments.append(instrument)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pm.write(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="将音频转换为MIDI")
    parser.add_argument("input", nargs="?", help="输入音频文件路径，例如 mp3/wav/flac 等")
    parser.add_argument("-o", "--output", help="输出MIDI文件路径，默认为同名 .mid")
    parser.add_argument("--sr", type=int, default=22050, help="采样率")
    parser.add_argument("--min_midi", type=int, default=36, help="最低MIDI音高")
    parser.add_argument("--max_midi", type=int, default=96, help="最高MIDI音高")
    parser.add_argument("--fps", type=int, default=100, help="每秒帧数用于分析")
    parser.add_argument("--instrument", type=int, default=0, help="MIDI乐器程序号，默认钢琴(0)")
    args = parser.parse_args()

    in_path = args.input
    if not in_path:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            in_path = filedialog.askopenfilename(
                title="选择音频文件",
                filetypes=[
                    ("音频文件", "*.wav *.mp3 *.flac *.ogg *.m4a"),
                    ("所有文件", "*.*"),
                ],
            )
        except Exception:
            in_path = ""
    in_path = os.path.abspath(in_path) if in_path else ""
    if not in_path or not os.path.isfile(in_path):
        print("找不到输入文件", file=sys.stderr)
        sys.exit(1)
    out_path = (
        os.path.abspath(args.output)
        if args.output
        else os.path.splitext(in_path)[0] + ".mid"
    )

    y, sr = load_audio(in_path, args.sr)
    notes = estimate_notes(y, sr, args.min_midi, args.max_midi, args.fps)
    write_midi(notes, args.instrument, out_path)
    print(f"已生成: {out_path}")


if __name__ == "__main__":
    main()