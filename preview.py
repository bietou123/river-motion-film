"""Render a short moving-image proof of concept, never a padded feature film."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
import numpy as np


ROOT = Path(__file__).resolve().parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ASSETS = Path(os.environ.get("FILM_ASSETS", ROOT / "assets"))
VOICE = (
    "河水一直往下流。工程表上的日期却不会挪。那天，机器还没等到标定完成。",
    "物料点过两遍。少的仍是那一件小东西。谁也没说，今天可以算了。",
    "履带把泥翻了一层又一层。我沿着草地、驾驶室和平台重走，试着记起被打断的那一秒。",
    "夜里回城，灯在路上掠过去。失去的究竟是器件，还是下班的时间？",
    "有人说，命盘里五行缺了木。我没有把它当答案。我只是想，什么时候能自己决定，往哪儿走、什么时候停，什么才算自己的生活。",
)


@dataclass(frozen=True)
class Shot:
    name: str
    source: str
    start: int
    duration: int
    crop: str | None
    caption: str
    tint: tuple[float, float]


SHOTS = (
    Shot("water", "river-4374-1080.mp4", 1, 20, None, "第一层平台", (1.07, 0.89)),
    Shot("count", "worker-4705-2160.mp4", 1, 12, "2160:1215:600:945", "少了一件", (1.03, 0.81)),
    Shot("search", "excavator-4153-1080.mp4", 12, 20, "1000:562:810:255", "从被打断的那一秒找起", (1.12, 0.82)),
    Shot("return", "city-11-1080.mp4", 0, 12, None, "又一次晚归", (1.08, 0.92)),
    Shot("exit", "forest-529-2160.mp4", 8, 18, None, "往外走", (1.06, 0.94)),
)


def call(args: list[str], *, cwd: Path | None = None, input_text: str | None = None) -> None:
    result = subprocess.run(args, cwd=cwd, input=input_text, text=True, encoding="utf-8",
                            capture_output=True, errors="replace", check=False,
                            env={**os.environ, "PYTHONUTF8": "1"})
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {args[0]}\n{result.stderr[-3500:]}")


def stamp(seconds: float) -> str:
    hours, rest = divmod(int(seconds), 3600)
    minutes, whole = divmod(rest, 60)
    centiseconds = round((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02}:{whole:02}.{centiseconds:02}"


def ass_for_shot(shot: Shot, index: int, width: int, directory: Path) -> Path:
    font = max(28, round(width * 0.022))
    title = max(42, round(width * 0.040))
    margin = round(width * 0.065)
    file = directory / f"shot-{index:02}.ass"
    events = [f"Dialogue: 0,{stamp(1)},{stamp(min(shot.duration - 1, 8))},Caption,,0,0,0,,{shot.caption}"]
    if index == 0:
        events = [
            f"Dialogue: 0,{stamp(2)},{stamp(8)},Title,,0,0,0,,第一层平台",
            f"Dialogue: 0,{stamp(3)},{stamp(8)},Small,,0,0,0,,受真实经历启发的虚构影像",
        ]
    if index == len(SHOTS) - 1:
        events += [f"Dialogue: 0,{stamp(shot.duration - 7)},{stamp(shot.duration - 1)},Credit,,0,0,0,,非实际现场影像 · 素材来自 Mixkit"]
    ass = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: " + str(width) +
        "\nPlayResY: " + str(round(width * 9 / 16)) + "\nWrapStyle: 0\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,"
        "Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Title,Microsoft YaHei,{title},&H00F4F5F3,&H00FFFFFF,&H90000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{margin},0,{margin * 2},1\n"
        f"Style: Caption,Microsoft YaHei,{font},&H00F4F5F3,&H00FFFFFF,&H90000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{margin},0,{margin},1\n"
        f"Style: Small,Microsoft YaHei,{max(22, font // 2)},&H00E4E5E1,&H00FFFFFF,&H90000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{margin},0,{round(margin * 1.55)},1\n"
        f"Style: Credit,Microsoft YaHei,{max(22, font // 2)},&H00F4F5F3,&H00FFFFFF,&H90000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{margin},0,{margin},1\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        + "\n".join(events) + "\n"
    )
    file.write_text(ass, encoding="utf-8-sig")
    return file


def render_shot(shot: Shot, index: int, assets: Path, cache: Path, width: int, fps: int,
                draft: bool) -> Path:
    source = assets / shot.source
    if not source.is_file() or source.stat().st_size < 1024:
        raise FileNotFoundError(f"Missing licensed footage: {source}; see SOURCES.md")
    caption = ass_for_shot(shot, index, width, cache)
    duration = min(3, shot.duration) if draft else shot.duration
    height = width * 9 // 16
    digest = hashlib.sha256((str(shot) + str(width) + str(fps) + caption.read_text(encoding="utf-8-sig")
                             + str(source.stat().st_size)).encode("utf-8")).hexdigest()[:12]
    output = cache / f"{index:02}-{digest}.mp4"
    if output.is_file() and output.stat().st_size > 1024:
        return output
    filters = []
    if shot.crop:
        filters.append(f"crop={shot.crop}")
    filters.extend([
        f"framerate=fps={fps}:interp_start=0:interp_end=255:scene=8",
        f"scale={width}:{height}:flags=lanczos",
        f"eq=contrast={shot.tint[0]}:saturation={shot.tint[1]}",
        f"subtitles={caption.name}",
        "format=yuv420p",
    ])
    command = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "warning",
               "-ss", str(shot.start), "-i", str(source), "-t", str(duration),
               "-vf", ",".join(filters), "-frames:v", str(duration * fps), "-an",
               "-c:v", "hevc_nvenc", "-preset", "p3", "-rc", "vbr", "-cq", "21",
               "-b:v", "18M", "-maxrate", "30M", "-bufsize", "36M", "-g", str(fps * 2),
               "-r", str(fps), "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
               "-color_trc", "bt709", "-colorspace", "bt709", "-y", str(output)]
    print(f"SHOT {index+1}/{len(SHOTS)} {shot.name} ({duration}s)", flush=True)
    call(command, cwd=cache)
    return output


def voice_samples(model: Path | None, text: str, cache: Path, index: int, samplerate: int,
                  kokoro: bool) -> np.ndarray:
    output = cache / (f"voice-{index:02}-kokoro.wav" if kokoro else f"voice-{index:02}.wav")
    if not kokoro:
        if model is None:
            raise ValueError("Piper voice model is missing")
        call(["piper", "--model", str(model), "--output_file", str(output),
              "--length-scale", "1.05", "--sentence-silence", "0.13"], input_text=text + "\n")
    with wave.open(str(output), "rb") as track:
        if track.getsampwidth() != 2 or track.getnchannels() != 1:
            raise RuntimeError("Piper must return mono 16-bit PCM")
        samples = np.frombuffer(track.readframes(track.getnframes()), dtype="<i2").astype(np.float32) / 32768
        original_rate = track.getframerate()
    positions = np.arange(round(len(samples) * samplerate / original_rate)) * original_rate / samplerate
    return np.interp(positions, np.arange(len(samples)), samples).astype(np.float32)


def prepare_kokoro(cache: Path, model: Path, python: Path, voice: str, draft: bool) -> None:
    entries = [{"text": line, "out": str(cache / f"voice-{index:02}-kokoro.wav")}
               for index, line in enumerate(VOICE) if not draft or index == 0]
    manifest = cache / "kokoro-lines.json"
    manifest.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    print("VOICE generating offline Mandarin narration", flush=True)
    call([str(python), str(ROOT / "voice_kokoro.py"), "--model-dir", str(model),
          "--voice", voice, "--lines", str(manifest)], cwd=ROOT)


def sound_effect(source: Path, length: int, samplerate: int, start: int) -> np.ndarray:
    if not source.is_file():
        raise FileNotFoundError(f"Missing licensed sound effect: {source}; see SOURCES.md")
    result = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error",
                             "-ss", str(start), "-i", str(source), "-t", str(length),
                             "-ac", "2", "-ar", str(samplerate), "-f", "f32le", "pipe:1"],
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    samples = np.frombuffer(result.stdout, dtype="<f4")
    if len(samples) != length * samplerate * 2:
        raise RuntimeError(f"Unexpected length for sound effect {source}")
    return samples.reshape(-1, 2)


def soundtrack(cache: Path, assets: Path, model: Path | None, draft: bool,
               kokoro_dir: Path | None, kokoro_python: Path | None, kokoro_voice: str) -> Path:
    samplerate = 48000
    lengths = [min(3, shot.duration) if draft else shot.duration for shot in SHOTS]
    size = sum(lengths) * samplerate
    time = np.arange(size, dtype=np.float64) / samplerate
    rng = np.random.default_rng(1386)
    # Long, non-looped air/water bed, filtered in the frequency domain.
    frequencies = np.fft.rfftfreq(size, 1 / samplerate)
    mix = np.empty((size, 2), dtype=np.float32)
    for channel in range(2):
        spectrum = np.fft.rfft(rng.standard_normal(size).astype(np.float32))
        spectrum *= 1.0 / np.sqrt(1.0 + (frequencies / 170.0) ** 2)
        air = np.fft.irfft(spectrum, n=size).astype(np.float32)
        mix[:, channel] = air * (0.008 / max(float(np.std(air)), 0.0001))
    offset = 0
    roots = (110.0, 130.81, 98.0, 82.41, 146.83)
    for index, length in enumerate(lengths):
        local = time[offset:offset + length * samplerate]
        t = local - local[0]
        envelope = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 0.75
        root = roots[index]
        pad = (np.sin(2 * np.pi * root * t) * 0.29 +
               np.sin(2 * np.pi * root * 1.498 * t) * 0.20 +
               np.sin(2 * np.pi * root * 2.001 * t) * 0.09)
        mix[offset:offset + length * samplerate] += ((pad * envelope * 0.036)[:, None]
                                                      * np.array([0.92, 1.03])).astype(np.float32)
        if index == 2:
            pulse = np.sin(2 * np.pi * 42 * t) * (np.sin(2 * np.pi * 0.33 * t) ** 4)
            mix[offset:offset + length * samplerate] += (pulse * 0.007 * envelope)[:, None].astype(np.float32)
        sound = (
            ("river-sfx-2454.wav", 5, 0.18),
            ("industrial-sfx-2504.wav", 8, 0.18),
            ("machinery-sfx-800.wav", 12, 0.18),
            ("traffic-sfx-2930.wav", 5, 0.25),
            ("river-sfx-2454.wav", 32, 0.15),
        )[index]
        if sound:
            name, source_offset, gain = sound
            field = sound_effect(assets / name, length, samplerate, source_offset)
            fade = np.minimum(np.minimum(t / 0.8, (length - t) / 0.8), 1.0)
            mix[offset:offset + length * samplerate] += field * fade[:, None] * gain
        offset += length * samplerate
    if kokoro_dir and kokoro_python:
        prepare_kokoro(cache, kokoro_dir, kokoro_python, kokoro_voice, draft)
    if (model and model.is_file()) or (kokoro_dir and kokoro_python):
        next_time = 0
        offset = 0
        for index, (line, length) in enumerate(zip(VOICE, lengths)):
            if draft and index > 0:
                offset += length
                continue
            voice = voice_samples(model, line, cache, index, samplerate, bool(kokoro_dir))
            position = max((offset + (0.5 if draft else 2)) * samplerate, next_time)
            position = int(position)
            take = min(len(voice), size - position)
            if take > 0:
                envelope = np.minimum(np.minimum(np.arange(take) / (0.38 * samplerate),
                                                 np.arange(take - 1, -1, -1) / (0.55 * samplerate)), 1.0)
                mix[position:position + take] *= (1.0 - envelope[:, None] * 0.68)
                mix[position:position + take] += voice[:take, None] * 0.90
                next_time = position + take + int(0.4 * samplerate)
            offset += length
    elif not draft:
        raise FileNotFoundError("A local Piper voice model is required for the narrated preview")
    mix = np.tanh(mix * 1.10)
    pcm = (np.clip(mix, -1.0, 1.0) * 32760).astype("<i2")
    output = cache / ("draft-score.wav" if draft else "score.wav")
    with wave.open(str(output), "wb") as track:
        track.setparams((2, 2, samplerate, 0, "NONE", "not compressed"))
        track.writeframes(pcm.tobytes())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--voice-model", type=Path, default=Path(os.environ["PIPER_MODEL"]) if "PIPER_MODEL" in os.environ else None)
    parser.add_argument("--kokoro-model-dir", type=Path, help="Local Apache-2.0 Mandarin Kokoro model directory")
    parser.add_argument("--kokoro-python", type=Path, help="Python executable with kokoro-onnx and misaki-fork[zh]")
    parser.add_argument("--kokoro-voice", default="zm_010")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "first-platform-preview-4k60.mp4")
    parser.add_argument("--draft", action="store_true", help="Five 3-second shots at 1280x720, 30 fps")
    args = parser.parse_args()
    if bool(args.kokoro_model_dir) != bool(args.kokoro_python):
        parser.error("--kokoro-model-dir and --kokoro-python must be provided together")
    width, fps = (1280, 30) if args.draft else (3840, 60)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = args.output.parent / "render-cache"
    cache.mkdir(exist_ok=True)
    shot_files = [render_shot(shot, index, args.assets, cache, width, fps, args.draft)
                  for index, shot in enumerate(SHOTS)]
    manifest = cache / "concat.txt"
    manifest.write_text("".join(f"file '{path.as_posix()}'\n" for path in shot_files), encoding="utf-8")
    silent = cache / ("draft-silent.mp4" if args.draft else "sample-silent.mp4")
    call([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-f", "concat", "-safe", "0",
          "-i", str(manifest), "-c", "copy", "-y", str(silent)])
    music = soundtrack(cache, args.assets, args.voice_model, args.draft,
                       args.kokoro_model_dir, args.kokoro_python, args.kokoro_voice)
    call([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(silent),
          "-i", str(music), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
          "-af", "loudnorm=I=-17:TP=-1.5:LRA=10",
          "-b:a", "192k", "-ar", "48000", "-t", str(sum(3 if args.draft else shot.duration for shot in SHOTS)),
          "-movflags", "+faststart", "-y", str(args.output)])
    print(f"PREVIEW {args.output} ({'draft' if args.draft else '3840x2160, 60fps, 82 seconds'})", flush=True)


if __name__ == "__main__":
    main()
