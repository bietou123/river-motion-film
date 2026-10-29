# 第一层平台 / The First Platform

An 85-second **moving-image proof of concept**, inspired by memories of site work,
repeated searches, late journeys and the need to decide one's own time. The horoscope
reference is a character's metaphor, not a factual prediction. There are no still
photos stretched to fill a timeline. The footage is representative licensed stock,
**not** documentary evidence of the person or workplace.

**Current status:** this is a short test, **not** the requested two-hour finished film.
The public release contains the edited test film; this repository contains the
complete editable renderer and source attribution, **not** the standalone stock
videos, sound effects, voice model, or personal memory files.

## Requirements

- Windows, Python 3.12 and `pip install -r requirements.txt`.
- NVIDIA GPU supported by FFmpeg's `hevc_nvenc`; `imageio-ffmpeg` supplies FFmpeg.
- A **locally stored** Kokoro Mandarin v1.1 model (`kokoro-v1.1-zh.onnx`,
  `voices-v1.1-zh.bin` and `config.json`). Model files are not part of this repository.
  Install the optional voice dependencies with `pip install -r requirements-voice.txt`
  in an isolated Python environment. The older `preview.py` can also use Piper.
- The individual Mixkit video clips and sound effects listed in
  [SOURCES.md](SOURCES.md). Place these in a local directory outside this repository. The renderer
  never bulk-downloads assets and does not redistribute third-party originals.

```powershell
python -X utf8 impact.py --draft --assets 'X:\your-footage'
python -X utf8 impact.py --assets 'X:\your-footage' --kokoro-model-dir 'X:\your-voice' --kokoro-python 'X:\your-voice\.venv\Scripts\python.exe'
python -X utf8 scan_motion.py output/first-platform-cinematic-soundmix-4k60.mp4 --gpu
python -m unittest discover -s tests
```

For a separately recorded human voice, pass `--narration-dir` instead of the
Kokoro options; that directory must contain `narrator-00.wav` through
`narrator-04.wav`. `preview.py` and `verify.py` retain the earlier 82-second cut.

The current short renders **85 seconds, 3840x2160, 60 fps, HEVC/AAC**, with
source-frame interpolation and real moving footage. Source footage varies between
1080p and native UHD, 23.976-30 fps. Enlarged/interpolated sources are not
represented as native 4K/60 capture. Ambience and foley use licensed field recordings;
default narration is synthetic speech from an offline Apache-licensed model and is
not represented as a human performance. `scan_motion.py` decodes every encoded frame
and reports repeats. The previous 82-second preview can be checked with `verify.py`.

Never publish your private birth chart, workplace media, internal project files,
voice model, or third-party originals with this code. The MIT license covers only
original source code; stock assets retain their providers' separate licenses.
