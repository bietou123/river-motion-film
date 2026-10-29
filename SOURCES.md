# Moving-image source ledger

The short proof of concept combines moving stock footage with recorded stock
sound, synthetic narration and editorial graphics. These are representative images, not recordings of the
person or the work site that inspired the fictional story. The clips are **not** part
of this source repository. Download each item individually under its own license and
store it outside the repository. Do not redistribute the source files with the code.

Check each clip against the [Mixkit Stock Video Free License](https://mixkit.co/license/#videoFree)
before using it. The license permits filmmaking and distribution of an edited film;
the [Mixkit terms](https://mixkit.co/terms/) prohibit scripted mass downloading and
offering items as a stock library. Verify the current license before reusing a clip.

| Local filename | Source page | Source format | Context |
| --- | --- | --- | --- |
| `river-4374-1080.mp4` | https://mixkit.co/free-stock-video/small-river-in-the-forest-4374/ | 1920x1080, 25 fps | Moving water |
| `worker-4705-2160.mp4` | https://mixkit.co/free-stock-video/young-worker-doing-inventory-4705/ | 3840x2160, 29.97 fps | Cropped to hands; no identity implied |
| `excavator-4153-1080.mp4` | https://mixkit.co/free-stock-video/excavator-trying-to-refloat-a-boat-4153/ | 1920x1080, 24 fps | Cropped to machinery; symbolic, not actual site |
| `city-11-1080.mp4` | https://mixkit.co/free-stock-video/aerial-view-of-city-traffic-at-night-11/ | 1920x1080, 23.976 fps | Moving night traffic |
| `forest-529-2160.mp4` | https://mixkit.co/free-stock-video/forest-stream-in-the-sunlight-529/ | 3840x2160, 23.976 fps | Moving drone / water |
| `digging-4069-1080.mp4` | [Mixkit stock video, item 4069](https://mixkit.co/free-stock-video/) | 1920x1080, 30 fps | Earthmoving / truck |
| `crane-4068-1080.mp4` | [Mixkit stock video, item 4068](https://mixkit.co/free-stock-video/) | 1920x1080, 30 fps | Machine beside water |
| `lightning-4059-1080.mp4` | [Mixkit stock video, item 4059](https://mixkit.co/free-stock-video/) | 1920x1080 | Real moving storm |

The movie output is encoded at 3840x2160, 60 fps. Original clips have the frame
rates above; intermediate frames are blended from adjacent moving frames and 1080p
sources are enlarged. Neither is described as native 4K/60 footage. No footage from
private workplaces or private memory files belongs in a public repository.

Sound effects are kept outside the repository as well. The [Mixkit Sound Effects Free
License](https://mixkit.co/license/#sfxFree) permits sound effects in films but expressly
forbids distributing the standalone sounds or including them with source files:

| Local filename | Source | Use |
| --- | --- | --- |
| `river-sfx-2454.wav` | https://mixkit.co/free-sound-effects/river/ (River water flowing, item 2454) | River and forest |
| `industrial-sfx-2504.wav` | https://mixkit.co/free-sound-effects/industrial/ (Industrial machine hum, item 2504) | Warehouse |
| `machinery-sfx-800.wav` | https://mixkit.co/free-sound-effects/construction/ (Construction place and bulldozer ambiance, item 800) | Machine |
| `traffic-sfx-2930.wav` | https://mixkit.co/free-sound-effects/traffic/ (City traffic background ambience, item 2930) | Night drive |
| `storm-rain-sfx-2390.wav` | https://mixkit.co/free-sound-effects/rain/ (item 2390) | Storm ambience |
| `rocks-sfx-400.wav` | https://mixkit.co/free-sound-effects/ (item 400) | Stone impact |
| `thunder-close-sfx-1300.wav` | https://mixkit.co/free-sound-effects/thunder/ (item 1300) | Delayed thunder |

The offline Mandarin narrator uses
[Kokoro-82M-v1.1-zh](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)
(Apache 2.0 model), [kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx)
(MIT runtime), and `misaki-fork[zh]`. None of their model files are committed here.
