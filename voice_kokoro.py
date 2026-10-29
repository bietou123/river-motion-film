"""Generate a Mandarin narration WAV with the locally installed Apache-licensed Kokoro model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro
from misaki import zh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--voice", default="zm_010")
    parser.add_argument("--speed", type=float, default=0.96)
    parser.add_argument("--text")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--lines", type=Path, help="UTF-8 JSON array of {text,out} entries")
    args = parser.parse_args()
    if not args.lines and (not args.text or not args.out):
        parser.error("pass --lines, or pass both --text and --out")
    if not 0.8 <= args.speed <= 1.2:
        parser.error("speed must be in [0.8, 1.2]")
    model = args.model_dir / "kokoro-v1.1-zh.onnx"
    voices = args.model_dir / "voices-v1.1-zh.bin"
    config = args.model_dir / "config.json"
    if not all(path.is_file() for path in (model, voices, config)):
        parser.error("missing Kokoro Mandarin model, voices, or config.json")
    g2p = zh.ZHG2P(version="1.1")
    speech = Kokoro(str(model), str(voices), vocab_config=str(config))
    entries = json.loads(args.lines.read_text(encoding="utf-8")) if args.lines else [
        {"text": args.text, "out": str(args.out)}
    ]
    for entry in entries:
        phonemes, _ = g2p(entry["text"])
        samples, samplerate = speech.create(
            phonemes, voice=args.voice, speed=args.speed, is_phonemes=True
        )
        output = Path(entry["out"])
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), samples, samplerate, subtype="PCM_16")
        print(f"VOICE {output} ({len(samples) / samplerate:.1f}s)", flush=True)


if __name__ == "__main__":
    main()
