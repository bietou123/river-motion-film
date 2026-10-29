"""Inspect encoded media and sample actual frame-to-frame changes in every shot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import av
import numpy as np

from preview import SHOTS


def motion_near(container: av.container.InputContainer, video: av.video.stream.VideoStream,
                second: float) -> dict[str, float]:
    container.seek(int(max(0.0, second - 1.5) * 1_000_000), any_frame=False, backward=True)
    images = []
    for frame in container.decode(video=video.index):
        moment = float(frame.pts * video.time_base)
        if moment < second:
            continue
        if moment > second + 0.55:
            break
        images.append(frame.reformat(width=256, height=144, format="gray").to_ndarray())
    differences = [float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))))
                   for a, b in zip(images, images[1:])]
    if len(differences) < 12:
        raise AssertionError(f"Too few decoded video frames at t={second}: {len(differences)}")
    return {"mean_luma_delta": round(float(np.mean(differences)), 3),
            "fraction_changed": round(float(np.mean(np.array(differences) > 0.08)), 3)}


def inspect(path: Path, width: int, fps: int, duration: int) -> dict:
    with av.open(str(path)) as container:
        streams = container.streams
        video, audio = streams.video[0], streams.audio[0]
        actual_duration = container.duration / av.time_base
        frame_rate = float(video.average_rate)
        if (video.width, video.height) != (width, width * 9 // 16):
            raise AssertionError(f"Wrong frame size: {video.width}x{video.height}")
        if abs(frame_rate - fps) > 0.01:
            raise AssertionError(f"Wrong frame rate: {frame_rate}")
        if abs(actual_duration - duration) > 0.3:
            raise AssertionError(f"Wrong duration: {actual_duration:.2f} vs {duration}")
        if video.codec_context.name != "hevc":
            raise AssertionError(f"Wrong codec: {video.codec_context.name}")
        if audio.codec_context.name != "aac":
            raise AssertionError(f"Missing AAC sound: {audio.codec_context.name}")
        if audio.layout.name != "stereo":
            raise AssertionError(f"Sound must be stereo: {audio.layout.name}")
        probes = {}
        position = 0
        for shot in SHOTS:
            length = min(3, shot.duration) if duration == 15 else shot.duration
            probes[shot.name] = motion_near(container, video, position + length * 0.55)
            position += length
        if sum(value["mean_luma_delta"] > 0.1 for value in probes.values()) < 4:
            raise AssertionError(f"Too many nearly static scenes: {probes}")
        return {"duration_seconds": round(actual_duration, 3), "resolution": [video.width, video.height],
                "fps": frame_rate, "codec": video.codec_context.name, "audio": audio.codec_context.name,
                "audio_layout": audio.layout.name,
                "motion_samples": probes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--draft", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.video, 1280 if args.draft else 3840,
                             30 if args.draft else 60, 15 if args.draft else 82),
                     ensure_ascii=False, indent=2))
