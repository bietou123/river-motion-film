"""Render every frame with the GPU; no image holds or duplicated frames."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

import glfw
import imageio_ffmpeg
import moderngl
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parent
FRAGMENT = ROOT / "world.frag"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
VERTEX = """#version 330 core
in vec2 in_pos;
out vec2 vUV;
void main() {
    vUV = (in_pos + 1.0) * 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""


class FilmRenderer:
    def __init__(self, width: int, height: int):
        if not glfw.init():
            raise RuntimeError("GLFW failed to initialize")
        glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        self.window = glfw.create_window(32, 32, "film-renderer", None, None)
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Unable to create GPU context")
        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context()
        self.ctx.viewport = (0, 0, width, height)
        self.program = self.ctx.program(vertex_shader=VERTEX, fragment_shader=FRAGMENT.read_text(encoding="utf-8"))
        random = np.random.default_rng(2026).integers(0, 256, (512, 512, 4), dtype=np.uint8)
        self.noise = self.ctx.texture((512, 512), 4, random.tobytes())
        self.noise.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.noise.repeat_x = True
        self.noise.repeat_y = True
        self.noise.use(location=0)
        self.program["uNoise"].value = 0
        quad = self.ctx.buffer(b"\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x80\xbf\x00\x00\x80\xbf\x00\x00\x80\x3f\x00\x00\x80\x3f\x00\x00\x80\x3f")
        self.quad = self.ctx.vertex_array(self.program, [(quad, "2f", "in_pos")])
        self.texture = self.ctx.texture((width, height), 4, dtype="f1")
        self.fbo = self.ctx.framebuffer(color_attachments=[self.texture])
        self.width, self.height = width, height
        self.program["uResolution"].value = width, height
        print(f"GPU: {self.ctx.info['GL_RENDERER']} | {width}x{height}", flush=True)

    def frame(self, seconds: float, scene: int) -> bytes:
        self.fbo.use()
        self.program["uTime"].value = seconds
        self.program["uScene"].value = float(scene)
        self.quad.render(mode=moderngl.TRIANGLE_STRIP)
        return self.fbo.read(components=4, alignment=1)

    def close(self):
        self.fbo.release()
        self.texture.release()
        self.noise.release()
        self.ctx.release()
        glfw.destroy_window(self.window)
        glfw.terminate()


def sequence_scene(seconds: float, preview: bool, fixed: int | None) -> int:
    if fixed is not None:
        return fixed
    if preview:
        return min(3, int(seconds // 8))
    return min(11, int(seconds // 600))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=3840)
    parser.add_argument("--height", type=int, default=2160)
    parser.add_argument("--scene", type=int, default=None)
    parser.add_argument("--time", type=float, default=12)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--duration", type=int, default=32)
    parser.add_argument("--benchmark", type=int, default=0, help="Measure this many rendered frames")
    parser.add_argument("--still", type=Path, help="Save one frame instead of encoding")
    parser.add_argument("--output", type=Path, default=ROOT / "sample-motion-4k60.mp4")
    parser.add_argument("--feature", action="store_true", help="Use the full 12-chapter, 7200s timeline")
    args = parser.parse_args()
    renderer = FilmRenderer(args.width, args.height)
    try:
        if args.still:
            pixels = renderer.frame(args.time, sequence_scene(args.time, not args.feature, args.scene))
            args.still.parent.mkdir(parents=True, exist_ok=True)
            Image.frombytes("RGBA", (args.width, args.height), pixels).convert("RGB").save(args.still)
            print(f"FRAME {args.still}", flush=True)
            return
        if args.benchmark:
            began = time.perf_counter()
            samples = []
            for index in range(args.benchmark):
                pixels = renderer.frame(index / args.fps, sequence_scene(index / args.fps, True, args.scene))
                if index in (0, args.benchmark // 2, args.benchmark - 1):
                    samples.append(hash(pixels[::16384]))
            elapsed = time.perf_counter() - began
            print(f"BENCHMARK {args.benchmark} frames / {elapsed:.2f}s = {args.benchmark / elapsed:.1f} fps; frame fingerprints {samples}", flush=True)
            return
        duration = 7200 if args.feature else args.duration
        args.output.parent.mkdir(parents=True, exist_ok=True)
        command = [FFMPEG, "-hide_banner", "-nostdin", "-loglevel", "error", "-f", "rawvideo",
                   "-pix_fmt", "rgba", "-s", f"{args.width}x{args.height}", "-r", str(args.fps),
                   "-i", "pipe:0", "-an", "-c:v", "hevc_nvenc", "-preset", "p1", "-rc", "vbr",
                   "-cq", "23", "-b:v", "10M", "-maxrate", "16M", "-g", "120",
                   "-movflags", "+faststart", "-y", str(args.output)]
        began = time.perf_counter()
        with subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE) as encoder:
            assert encoder.stdin and encoder.stderr
            try:
                for index in range(duration * args.fps):
                    seconds = index / args.fps
                    encoder.stdin.write(renderer.frame(seconds, sequence_scene(seconds, not args.feature, args.scene)))
                    if index and index % (args.fps * 5) == 0:
                        print(f"ENCODE {index}/{duration * args.fps} | {time.perf_counter() - began:.1f}s elapsed", flush=True)
            except BrokenPipeError as error:
                raise RuntimeError(encoder.stderr.read().decode(errors="replace")) from error
            finally:
                encoder.stdin.close()
            message = encoder.stderr.read().decode(errors="replace")
            if encoder.wait():
                raise RuntimeError(f"FFmpeg failed: {message}")
        print(f"VIDEO {args.output} in {time.perf_counter() - began:.1f}s", flush=True)
    finally:
        renderer.close()


if __name__ == "__main__":
    main()
