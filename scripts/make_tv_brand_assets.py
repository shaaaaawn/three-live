#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Renders the Apple TV demo's layered app icon and Top Shelf images.

Writes `App Icon & Top Shelf Image.brandassets` into
`mobile/examples/ios_swiftui/TVAssets.xcassets`. The back layer of every icon is fully
opaque (App Store validation rejects alpha there); the middle and front layers are
transparent so tvOS can apply its parallax effect.

Usage: python3 scripts/make_tv_brand_assets.py   (requires Pillow)
"""

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "mobile/examples/ios_swiftui/TVAssets.xcassets"
BRAND = CATALOG / "App Icon & Top Shelf Image.brandassets"

NAVY_TOP = (11, 18, 32)
NAVY_BOTTOM = (20, 33, 61)
SKY = (56, 189, 248)
VIOLET = (168, 85, 247)
WHITE = (241, 245, 249)
INFO = {"author": "xcode", "version": 1}


def write_json(path: Path, payload: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "Contents.json").write_text(json.dumps({**payload, "info": INFO}, indent=2) + "\n")


def back(w: int, h: int) -> Image.Image:
    """Opaque vertical gradient with a soft floor glow."""
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        row = tuple(int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM))
        for x in range(w):
            px[x, y] = row
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(
        (w * 0.15, h * 0.62, w * 0.85, h * 1.05), fill=90)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(w, h) / 18))
    tint = Image.new("RGB", (w, h), SKY)
    return Image.composite(tint, img, glow).convert("RGB")


def rings(w: int, h: int, cx: float, cy: float, r: float) -> Image.Image:
    """Transparent layer: two tilted orbit rings around a sphere, as in the demo scenes."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    stroke = max(2, int(r * 0.07))
    for color, tilt in ((SKY, 0.36), (VIOLET, -0.36)):
        pts = []
        for i in range(181):
            a = 2 * math.pi * i / 180
            x, y = r * 1.55 * math.cos(a), r * 0.48 * math.sin(a)
            pts.append((cx + x * math.cos(tilt) - y * math.sin(tilt),
                        cy + x * math.sin(tilt) + y * math.cos(tilt)))
        d.line(pts, fill=color + (255,), width=stroke, joint="curve")
    return layer


def sphere(w: int, h: int, cx: float, cy: float, r: float) -> Image.Image:
    """Transparent layer: a shaded sphere with a specular highlight."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = layer.load()
    lx, ly = -0.45, -0.55
    for y in range(int(cy - r), int(cy + r) + 1):
        for x in range(int(cx - r), int(cx + r) + 1):
            nx, ny = (x - cx) / r, (y - cy) / r
            d2 = nx * nx + ny * ny
            if d2 > 1 or not (0 <= x < w and 0 <= y < h):
                continue
            nz = math.sqrt(1 - d2)
            facing = nx * lx + ny * ly  # > 0 on the side facing the upper-left light
            diffuse = max(0.0, facing * 0.8 + nz * 0.6)
            spec = max(0.0, nz * 0.7 + facing * 0.7) ** 24
            c = [min(255, int(v * (0.25 + 0.75 * diffuse) + 255 * spec)) for v in WHITE]
            edge = min(1.0, (1 - math.sqrt(d2)) * r / 1.5)
            px[x, y] = (c[0], c[1], c[2], int(255 * edge))
    return layer


def wordmark(img: Image.Image, text: str, size: int, xy: tuple) -> None:
    font = None
    for name in ("/System/Library/Fonts/SFNSRounded.ttf", "/System/Library/Fonts/SFNS.ttf",
                 "/System/Library/Fonts/Helvetica.ttc"):
        try:
            font = ImageFont.truetype(name, size)
            break
        except OSError:
            continue
    ImageDraw.Draw(img).text(xy, text, fill=WHITE + (255,), font=font or ImageFont.load_default(),
                             anchor="lm")


def icon_stack(name: str, w: int, h: int, scales: tuple) -> None:
    stack = BRAND / f"{name}.imagestack"
    layers = ("Front", "Middle", "Back")
    write_json(stack, {"layers": [{"filename": f"{l}.imagestacklayer"} for l in layers]})
    for layer in layers:
        content = stack / f"{layer}.imagestacklayer" / "Content.imageset"
        write_json(stack / f"{layer}.imagestacklayer", {})
        images = []
        for s in scales:
            W, H = w * s, h * s
            cx, cy, r = W / 2, H / 2, H * 0.17
            img = {"Back": lambda: back(W, H),
                   "Middle": lambda: rings(W, H, cx, cy, r),
                   "Front": lambda: sphere(W, H, cx, cy, r)}[layer]()
            fname = f"{layer.lower()}-{w}x{h}@{s}x.png"
            content.mkdir(parents=True, exist_ok=True)
            img.save(content / fname)
            images.append({"filename": fname, "idiom": "tv", "scale": f"{s}x"})
        write_json(content, {"images": images})


def top_shelf(name: str, w: int, h: int) -> None:
    imageset = BRAND / f"{name}.imageset"
    images = []
    for s in (1, 2):
        W, H = w * s, h * s
        img = back(W, H).convert("RGBA")
        cx, cy, r = H * 0.62, H / 2, H * 0.2
        img.alpha_composite(rings(W, H, cx, cy, r))
        img.alpha_composite(sphere(W, H, cx, cy, r))
        wordmark(img, "Three-Live", int(H * 0.16), (H * 1.25, H * 0.5))
        fname = f"{name.lower().replace(' ', '-')}-{w}x{h}@{s}x.png"
        imageset.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(imageset / fname)
        images.append({"filename": fname, "idiom": "tv", "scale": f"{s}x"})
    write_json(imageset, {"images": images})


def main() -> None:
    write_json(CATALOG, {})
    write_json(BRAND, {"assets": [
        {"filename": "App Icon - App Store.imagestack", "idiom": "tv",
         "role": "primary-app-icon", "size": "1280x768"},
        {"filename": "App Icon.imagestack", "idiom": "tv",
         "role": "primary-app-icon", "size": "400x240"},
        {"filename": "Top Shelf Image Wide.imageset", "idiom": "tv",
         "role": "top-shelf-image-wide", "size": "2320x720"},
        {"filename": "Top Shelf Image.imageset", "idiom": "tv",
         "role": "top-shelf-image", "size": "1920x720"},
    ]})
    icon_stack("App Icon - App Store", 1280, 768, (1,))
    icon_stack("App Icon", 400, 240, (1, 2))
    top_shelf("Top Shelf Image", 1920, 720)
    top_shelf("Top Shelf Image Wide", 2320, 720)


if __name__ == "__main__":
    main()
