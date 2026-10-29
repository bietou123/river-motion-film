"""A sound-led, continuously moving cinematic sequence; not a feature-length film."""

from __future__ import annotations

import argparse
import hashlib
import json
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from preview import ASSETS, FFMPEG, ROOT, call, sound_effect, stamp


@dataclass(frozen=True)
class Shot:
    name: str
    source: str
    start: float
    duration: int
    speed: float
    field: str
    field_offset: int
    field_gain: float
    crop: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class Foley:
    source: str
    source_start: int
    duration: int
    at: float
    gain: float
    left: float = 1.0
    right: float = 1.0


SHOTS = (
    Shot("weight", "digging-4069-1080.mp4", 25, 10, 1.8, "machinery-sfx-800.wav", 12, 0.30),
    Shot("current", "river-4374-1080.mp4", 1, 9, 1, "river-sfx-2454.wav", 5, 0.23),
    Shot("inventory", "worker-4705-2160.mp4", 2, 8, 1, "industrial-sfx-2504.wav", 8, 0.16,
         "2160:1215:600:945"),
    Shot("work", "crane-4068-1080.mp4", 5, 8, 1.4, "machinery-sfx-800.wav", 39, 0.24),
    Shot("impact", "digging-4069-1080.mp4", 54, 13, 2, "machinery-sfx-800.wav", 54, 0.30),
    Shot("flash", "lightning-4059-1080.mp4", 9, 5, 1, "storm-rain-sfx-2390.wav", 8, 0.55),
    Shot("city", "city-11-1080.mp4", 0, 12, 1, "traffic-sfx-2930.wav", 7, 0.42),
    Shot("path", "forest-529-2160.mp4", 4, 20, 1, "river-sfx-2454.wav", 42, 0.14,
         title="第一层平台"),
)

LINES = (
    (1.0, "那天，机器还在动。人却已经被时间追上了。"),
    (21.0, "少了一件标定仪器。白天走过的路，夜里要再走一遍。"),
    (40.0, "石头落进车斗。表上的日期，一格也没松动。"),
    (55.0, "到了夜里，我想的不是明天还能赚多少。"),
    (69.0, "有人说，命盘里缺木。这不是判词。路要怎么走，我自己定。"),
)

# First rock hit is 0.25s into the trimmed recording, at 38.50s on screen.
# Thunder attacks 0.45s into its recording, 0.60s after the 50.60s flash.
FOLEY = (
    Foley("rocks-sfx-400.wav", 2, 2, 38.25, 0.75, 1.0, 0.82),
    Foley("thunder-close-sfx-1300.wav", 0, 8, 50.75, 0.49),
)
CROSSFADE = 0.5


def subtitle(shot: Shot, index: int, width: int, cache: Path) -> Path:
    output = cache / f"impact-{index:02}.ass"
    size = max(48, round(width * 0.04))
    left = round(width * 0.065)
    lines = []
    if shot.title:
        lines.append(f"Dialogue: 0,{stamp(shot.duration - 8)},{stamp(shot.duration - 1)},Title,,0,0,0,,{shot.title}")
        lines.append(f"Dialogue: 0,{stamp(shot.duration - 7)},{stamp(shot.duration - 1)},Small,,0,0,0,,受真实经历启发的虚构影像")
    ass = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {width * 9 // 16}\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,"
        "Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,"
        "Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Title,Microsoft YaHei,{size},&H00FCFCF6,&H00FFFFFF,&HA0000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{left},0,{left * 2},1\n"
        f"Style: Small,Microsoft YaHei,{max(26, size // 3)},&H00E8E8E4,&H00FFFFFF,&HA0000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,2,0,1,{left},0,{round(left * 1.5)},1\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
        + "\n".join(lines) + "\n"
    )
    output.write_text(ass, encoding="utf-8-sig")
    return output


def render_shot(shot: Shot, index: int, assets: Path, cache: Path, width: int, fps: int,
                draft: bool) -> Path:
    source = assets / shot.source
    if not source.is_file() or source.stat().st_size < 1024:
        raise FileNotFoundError(f"Missing licensed footage: {source}; see SOURCES.md")
    subs = subtitle(shot, index, width, cache)
    duration = min(2, shot.duration) if draft else shot.duration
    digest = hashlib.sha256((str(shot) + str(width) + str(fps) + str(duration) +
                             subs.read_text(encoding="utf-8-sig") + str(source.stat().st_size)).encode()).hexdigest()[:12]
    output = cache / f"{index:02}-{digest}.mp4"
    if output.is_file() and output.stat().st_size > 1024:
        return output
    filters = [f"setpts=(PTS-STARTPTS)/{shot.speed}"]
    if shot.crop:
        filters.append(f"crop={shot.crop}")
    filters += [f"framerate=fps={fps}:interp_start=0:interp_end=255:scene=8",
                f"scale={width}:{width * 9 // 16}:flags=lanczos",
                "eq=contrast=1.09:saturation=0.85", f"subtitles={subs.name}", "format=yuv420p"]
    print(f"SHOT {index+1}/{len(SHOTS)} {shot.name} ({duration}s)", flush=True)
    call([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "warning", "-ss", str(shot.start),
          "-i", str(source), "-t", str(duration), "-vf", ",".join(filters),
          "-frames:v", str(duration * fps), "-an", "-c:v", "hevc_nvenc", "-preset", "p3",
          "-rc", "vbr", "-cq", "20", "-b:v", "20M", "-maxrate", "34M", "-bufsize", "40M",
          "-g", str(fps * 2), "-r", str(fps), "-pix_fmt", "yuv420p",
          "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
          "-y", str(output)], cwd=cache)
    return output


def generated_voices(cache: Path, model: Path, python: Path) -> list[Path]:
    files = [cache / f"narrator-{i:02}.wav" for i in range(len(LINES))]
    manifest = cache / "narration.json"
    manifest.write_text(json.dumps([{"text": line, "out": str(file)}
                                    for (_, line), file in zip(LINES, files)], ensure_ascii=False), encoding="utf-8")
    call([str(python), str(ROOT / "voice_kokoro.py"), "--model-dir", str(model),
          "--voice", "zm_010", "--speed", "0.96", "--lines", str(manifest)], cwd=ROOT)
    return files


def scene_envelope(seconds: np.ndarray, start: int, end: int,
                   first: bool, last: bool) -> np.ndarray:
    if first:
        fade_in = np.clip(seconds / 0.35, 0.0, 1.0)
    else:
        phase = np.clip((seconds - start + CROSSFADE) / (2 * CROSSFADE), 0.0, 1.0)
        fade_in = np.sin(phase * np.pi / 2)
    if last:
        fade_out = np.clip((end - seconds) / 0.8, 0.0, 1.0)
    else:
        phase = np.clip((seconds - end + CROSSFADE) / (2 * CROSSFADE), 0.0, 1.0)
        fade_out = np.cos(phase * np.pi / 2)
    return fade_in * fade_out


def read_voice(path: Path, rate: int) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Missing recorded narration: {path}")
    import subprocess

    result = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error",
                             "-i", str(path), "-vn", "-af", "highpass=f=75",
                             "-ac", "1", "-ar", str(rate), "-f", "f32le", "pipe:1"],
                            capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"Could not decode narration {path}: {result.stderr.decode(errors='replace')}")
    samples = np.frombuffer(result.stdout, dtype="<f4").copy()
    if len(samples) < rate // 2:
        raise ValueError(f"Narration is too short: {path}")
    return samples


def audio_track(cache: Path, assets: Path, model: Path | None, python: Path | None,
                draft: bool, narration_dir: Path | None = None) -> Path:
    rate = 48000
    lengths = [min(2, shot.duration) if draft else shot.duration for shot in SHOTS]
    size = sum(lengths) * rate
    mix = np.zeros((size, 2), dtype=np.float32)
    offset = 0
    for index, (shot, length) in enumerate(zip(SHOTS, lengths)):
        lead, tail = (index > 0), (index < len(SHOTS) - 1)
        position = offset - int(lead)
        field = sound_effect(assets / shot.field, length + int(lead) + int(tail),
                             rate, shot.field_offset)
        times = position + np.arange(len(field), dtype=np.float32) / rate
        fade = scene_envelope(times, offset, offset + length, not lead, not tail)
        clip_start = max(0, position * rate)
        clip_end = min(size, (position + len(field) // rate) * rate)
        src_start = clip_start - position * rate
        count = clip_end - clip_start
        mix[clip_start:clip_end] += (field[src_start:src_start + count]
                                     * fade[src_start:src_start + count, None] * shot.field_gain)
        offset += length
    if not draft:
        for cue in FOLEY:
            data = sound_effect(assets / cue.source, cue.duration, rate, cue.source_start)
            local = np.arange(len(data), dtype=np.float32) / rate
            fade = np.clip(local / 0.01, 0.0, 1.0) * np.clip((cue.duration - local) / 0.25, 0.0, 1.0)
            pos = round(cue.at * rate)
            count = min(len(data), size - pos)
            mix[pos:pos + count] += (data[:count] * fade[:count, None] * cue.gain
                                      * [cue.left, cue.right])
        if narration_dir:
            voices = [narration_dir / f"narrator-{i:02}.wav" for i in range(len(LINES))]
        elif model and python:
            voices = generated_voices(cache, model, python)
        else:
            raise FileNotFoundError("Pass --narration-dir for human recordings or both Kokoro options")
        for (at, _), file in zip(LINES, voices):
            speech = read_voice(file, rate)
            pos = round(at * rate)
            take = min(len(speech), size - pos)
            if take < rate // 2:
                raise ValueError(f"Narration starts after the picture ends: {file}")
            rise = np.clip(np.arange(take) / (rate * 0.20), 0.0, 1.0)
            fall = np.clip(np.arange(take - 1, -1, -1) / (rate * 0.50), 0.0, 1.0)
            blend = rise * fall
            mix[pos:pos + take] *= 1.0 - blend[:, None] * 0.55
            voice_stereo = np.column_stack((speech[:take], speech[:take])) * blend[:, None]
            # Short asymmetric early reflections give a dry close voice a modest room size.
            left_delay, right_delay = round(0.029 * rate), round(0.041 * rate)
            voice_stereo[left_delay:, 0] += speech[:take - left_delay] * blend[:take - left_delay] * 0.055
            voice_stereo[right_delay:, 1] += speech[:take - right_delay] * blend[:take - right_delay] * 0.045
            mix[pos:pos + take] += voice_stereo * 0.91
    peak = float(np.max(np.abs(mix)))
    if peak > 0.94:
        mix *= 0.94 / peak
    pcm = (np.clip(mix, -1.0, 1.0) * 32767).astype("<i2")
    output = cache / ("draft-score.wav" if draft else "score.wav")
    with wave.open(str(output), "wb") as track:
        track.setparams((2, 2, rate, 0, "NONE", "not compressed"))
        track.writeframes(pcm.tobytes())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, default=ASSETS)
    parser.add_argument("--kokoro-model-dir", type=Path)
    parser.add_argument("--kokoro-python", type=Path)
    parser.add_argument("--narration-dir", type=Path,
                        help="Five human recordings named narrator-00.wav through narrator-04.wav")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "first-platform-cinematic-soundmix-4k60.mp4")
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()
    if bool(args.kokoro_model_dir) != bool(args.kokoro_python):
        parser.error("--kokoro-model-dir and --kokoro-python must be provided together")
    if args.narration_dir and args.kokoro_model_dir:
        parser.error("Choose either human recordings or Kokoro, not both")
    args.output = args.output.resolve()
    args.assets = args.assets.resolve()
    if args.narration_dir:
        args.narration_dir = args.narration_dir.resolve()
    width, fps = (1280, 30) if args.draft else (3840, 60)
    cache = args.output.parent / "impact-cache"
    cache.mkdir(parents=True, exist_ok=True)
    output_files = [render_shot(shot, i, args.assets, cache, width, fps, args.draft)
                    for i, shot in enumerate(SHOTS)]
    manifest = cache / "sequence.txt"
    manifest.write_text("".join(f"file '{path.as_posix()}'\n" for path in output_files), encoding="utf-8")
    silent = cache / ("draft-silent.mp4" if args.draft else "silent.mp4")
    call([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-f", "concat", "-safe", "0",
          "-i", str(manifest), "-c", "copy", "-y", str(silent)])
    sound = audio_track(cache, args.assets, args.kokoro_model_dir, args.kokoro_python,
                        args.draft, args.narration_dir)
    call([FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(silent),
          "-i", str(sound), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
          "-af", "loudnorm=I=-18:TP=-2:LRA=11", "-b:a", "256k", "-ar", "48000",
          "-movflags", "+faststart", "-y", str(args.output)])
    print(f"CINEMATIC TEST {args.output} ({sum(lengths for lengths in [min(2, s.duration) if args.draft else s.duration for s in SHOTS])}s)", flush=True)


if __name__ == "__main__":
    main()
