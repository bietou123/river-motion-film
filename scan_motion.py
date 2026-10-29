"""Decode every frame; report exact repeats and stretches with negligible image motion."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import av
import numpy as np

from preview import FFMPEG


def cpu_frames(video_path: Path):
    with av.open(str(video_path)) as container:
        video = container.streams.video[0]
        for frame in container.decode(video=video.index):
            yield frame.reformat(width=256, height=144, format="gray").to_ndarray()


def gpu_frames(video_path: Path):
    command = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-hwaccel", "cuda",
               "-hwaccel_output_format", "cuda", "-c:v", "hevc_cuvid", "-i", str(video_path),
               "-an", "-vf", "scale_cuda=256:144,hwdownload,format=nv12,format=gray",
               "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        assert process.stdout and process.stderr
        bytes_per_frame = 256 * 144
        while raw := process.stdout.read(bytes_per_frame):
            if len(raw) != bytes_per_frame:
                raise RuntimeError("GPU decoded a truncated frame")
            yield np.frombuffer(raw, dtype=np.uint8).reshape(144, 256)
        error = process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            raise RuntimeError(f"GPU decode failed: {error}")


def scan(video_path: Path, threshold: float = 0.08, gpu: bool = False) -> dict:
    exact = []
    quiet = []
    previous = None
    count = 0
    longest_quiet = 0
    quiet_run = 0
    lowest = (float("inf"), 0)
    with av.open(str(video_path)) as container:
        fps = float(container.streams.video[0].average_rate)
    started = time.perf_counter()
    for image in gpu_frames(video_path) if gpu else cpu_frames(video_path):
        if previous is not None:
            delta = float(np.mean(np.abs(image.astype(np.int16) - previous.astype(np.int16))))
            if delta == 0:
                exact.append(count)
            if delta < threshold:
                quiet.append(count)
                quiet_run += 1
                longest_quiet = max(longest_quiet, quiet_run)
                if delta < lowest[0]:
                    lowest = (delta, count)
            else:
                quiet_run = 0
        previous = image
        count += 1
    return {"frames": count, "fps": fps, "exact_repeat_count": len(exact),
            "exact_repeats_first": [round(n / fps, 2) for n in exact[:16]],
            "nearly_still_count": len(quiet), "longest_nearly_still_frames": longest_quiet,
            "nearly_still_first": [round(n / fps, 2) for n in quiet[:16]],
            "least_motion": {"delta": round(lowest[0], 4), "second": round(lowest[1] / fps, 2)},
            "scan_seconds": round(time.perf_counter() - started, 1)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--threshold", type=float, default=0.08)
    parser.add_argument("--gpu", action="store_true", help="Use NVIDIA decoding and resizing")
    args = parser.parse_args()
    report = scan(args.video, args.threshold, args.gpu)
    print(json.dumps(report, indent=2))
    if report["exact_repeat_count"]:
        raise SystemExit("FAIL: the video contains identical adjacent frames")
