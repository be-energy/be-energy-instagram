#!/usr/bin/env python3
"""Genera un Reel animado (1080x1920, 30 fps, MP4 H.264) a partir de post.json.

Uso:  python scripts/render_reel.py queue/2026-11-26-reel-potencia [--preview]

post.json de un reel:
{
  "kind": "reel",
  "publish_at": "2026-11-26T10:00:00+01:00",
  "topic": "...",
  "caption": "...",
  "scenes": [
    {"type": "cover", "kicker": "...", "title": "... *resaltado* ..."},
    {"type": "point", "n": 1, "title": "...", "body": "..."},
    {"type": "stat", "value": "365 días", "label": "...", "kicker": "..."},
    {"type": "cta", "title": "...", "body": "...", "button": "..."}
  ]
}
Escribe reel.mp4 y cover.jpg (portada) en la carpeta. Con --preview solo dibuja
el último fotograma de cada escena como preview_XX.jpg, sin vídeo.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import (GREY_L, LIGHT, LIME, TEAL, TEAL_2, WHITE, ROOT, bebas, dm,  # noqa: E402
                    draw_lines, fit)

W, H = 1080, 1920
M = 96
FPS = 30
SAFE_TOP, SAFE_BOTTOM = 260, H - 420  # zona sin tapar por la interfaz de Reels


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


class Scene:
    """Fondo fijo + elementos que entran animados en momentos distintos."""

    def __init__(self, bg, dark):
        self.bg = bg
        self.dark = dark
        self.items = []  # (layer RGBA recortada, (x, y), start, anim)

    def add(self, draw_fn, start, anim="up"):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(layer), layer)
        box = layer.getbbox()
        if box:
            self.items.append((layer.crop(box), (box[0], box[1]), start, anim))

    def frame(self, t):
        img = self.bg.copy()
        for layer, (x, y), start, anim in self.items:
            p = ease((t - start) / 0.45)
            if p <= 0:
                continue
            lay = layer
            dx = dy = 0
            if anim == "up":
                dy = int((1 - p) * 60)
            elif anim == "left":
                dx = int((1 - p) * -80)
            elif anim == "scale":
                s = 0.6 + 0.4 * p + 0.06 * math.sin(p * math.pi)
                lay = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.LANCZOS)
                dx = (layer.width - lay.width) // 2
                dy = (layer.height - lay.height) // 2
            if p < 1:
                a = lay.getchannel("A").point(lambda v, p=p: int(v * p))
                lay = lay.copy()
                lay.putalpha(a)
            img.paste(lay, (x + dx, y + dy), lay)
        return img


def background(dark, deco=True):
    img = Image.new("RGB", (W, H), TEAL if dark else LIGHT)
    if deco:
        d = ImageDraw.Draw(img)
        d.ellipse([W - 260, 230, W + 260, 750], outline=LIME, width=20)
    logo = Image.open(ROOT / "assets" / ("logo_dark.png" if dark else "logo_color.png")).convert("RGBA")
    lw = 190
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.paste(logo, (M, SAFE_BOTTOM + 40), logo)
    return img


def text_block(scene, text, fontfn, sizes, maxh, color, hl, y, start, lh=1.0, marker=None, align="left", stagger=0.12):
    """Añade un bloque de texto línea a línea (cada línea entra con retraso). Devuelve (y_final, t_final)."""
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f, lines, size = fit(probe, text, fontfn, W - 2 * M, maxh, sizes, lh)
    t = start
    for line in lines:
        yy = y
        scene.add(lambda d, _l, line=line, yy=yy: draw_lines(d, [line], f, M, yy, size, color, hl, lh, marker=marker,
                                                            align=align, maxw=W - 2 * M), t)
        y += size * lh
        t += stagger
    return y, t


def measure(text, fontfn, sizes, maxh, lh):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f, lines, size = fit(probe, text, fontfn, W - 2 * M, maxh, sizes, lh)
    return len(lines) * size * lh


def scene_cover(s):
    sc = Scene(background(True), True)
    th = measure(s["title"], bebas, range(190, 90, -6), 820, 0.95)
    total = (110 if s.get("kicker") else 0) + th + (40 + 160 if s.get("subtitle") else 0)
    y = SAFE_TOP + max((SAFE_BOTTOM - SAFE_TOP - total) / 2, 0)
    t = 0.2
    if s.get("kicker"):
        k = s["kicker"].upper()

        def kick(d, _l, y=y):
            f = dm(34, 700)
            tw = d.textlength(k, font=f)
            d.rounded_rectangle([M, y, M + tw + 52, y + 68], radius=34, fill=LIME)
            d.text((M + 26, y + 14), k, font=f, fill=TEAL)
        sc.add(kick, t, "left")
        y += 110
        t += 0.3
    y, t = text_block(sc, s["title"], bebas, range(190, 90, -6), 820, WHITE, LIME, y, t, 0.95)
    if s.get("subtitle"):
        y, t = text_block(sc, s["subtitle"], lambda z: dm(z, 400), range(48, 32, -2), 220, GREY_L, LIME, y + 40, t + 0.2, 1.35)
    return sc, t


def scene_point(s):
    sc = Scene(background(False), False)
    th = measure(s["title"], bebas, range(150, 76, -4), 520, 0.98)
    bh = measure(s.get("body", ""), lambda z: dm(z, 450), range(58, 36, -2), 520, 1.38) if s.get("body") else 0
    total = (230 if s.get("n") is not None else 0) + th + 100 + bh
    y = SAFE_TOP + max((SAFE_BOTTOM - SAFE_TOP - total) / 2, 0)
    t = 0.15
    if s.get("n") is not None:
        n = str(s["n"]).zfill(2)

        def num(d, _l, y=y):
            d.ellipse([M, y, M + 160, y + 160], fill=LIME)
            f = bebas(116)
            tw = d.textlength(n, font=f)
            d.text((M + 80 - tw / 2, y + 24), n, font=f, fill=TEAL)
        sc.add(num, t, "scale")
        y += 230
        t += 0.3
    y, t = text_block(sc, s["title"], bebas, range(150, 76, -4), 520, TEAL, TEAL, y, t, 0.98, marker=LIME)
    y += 34
    sc.add(lambda d, _l, y=y: d.rectangle([M, y, M + 110, y + 10], fill=LIME), t, "left")
    y += 66
    if s.get("body"):
        y, t = text_block(sc, s["body"], lambda z: dm(z, 450), range(58, 36, -2), 520, TEAL_2, TEAL, y, t + 0.2, 1.38,
                          marker=(220, 234, 160), stagger=0.08)
    return sc, t


def scene_stat(s):
    sc = Scene(background(True), True)
    vh = measure(s["value"], bebas, range(420, 140, -10), 520, 0.9)
    lh_ = measure(s.get("label", ""), lambda z: dm(z, 500), range(64, 36, -2), 360, 1.3)
    total = (100 if s.get("kicker") else 0) + vh + 40 + lh_
    y = SAFE_TOP + max((SAFE_BOTTOM - SAFE_TOP - total) / 2, 0)
    t = 0.15
    if s.get("kicker"):
        k = s["kicker"].upper()
        sc.add(lambda d, _l, y=y: d.text((M, y), k, font=dm(40, 700), fill=LIME), t, "left")
        y += 100
        t += 0.25
    y, t = text_block(sc, s["value"], bebas, range(420, 140, -10), 520, LIME, LIME, y, t, 0.9)
    y, t = text_block(sc, s.get("label", ""), lambda z: dm(z, 500), range(64, 36, -2), 360, WHITE, LIME, y + 40, t + 0.25, 1.3)
    if s.get("note"):
        y, t = text_block(sc, s["note"], lambda z: dm(z, 400), range(42, 30, -2), 260, GREY_L, LIME, y + 50, t + 0.2, 1.38)
    return sc, t


def scene_cta(s):
    bg = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(bg)
    d.ellipse([-320, H - 620, 320, H + 20], outline=LIME, width=20)
    d.ellipse([W - 260, 230, W + 260, 750], outline=LIME, width=20)
    sc = Scene(bg, True)
    logo = Image.open(ROOT / "assets" / "logo_dark.png").convert("RGBA")
    lw = 420
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    title = s.get("title", "¿Pagas de más en tu *luz?*")
    th = measure(title, bebas, range(150, 80, -4), 400, 0.98)
    bh = measure(s.get("body", ""), lambda z: dm(z, 450), range(50, 32, -2), 240, 1.35) if s.get("body") else 0
    total = logo.height + 90 + th + 40 + bh + 70 + 110
    y = SAFE_TOP + max((SAFE_BOTTOM - SAFE_TOP - total) / 2, 0)
    t = 0.1
    sc.add(lambda d, l, y=y: l.paste(logo, (int((W - lw) / 2), int(y)), logo), t, "scale")
    y += logo.height + 90
    t += 0.35
    y, t = text_block(sc, title, bebas, range(150, 80, -4), 400, WHITE, LIME, y, t, 0.98, align="center")
    if s.get("body"):
        y, t = text_block(sc, s["body"], lambda z: dm(z, 450), range(50, 32, -2), 240, GREY_L, LIME, y + 40, t + 0.15, 1.35, align="center")
    y += 70
    btn = s.get("button", "Estudio gratuito · be-energy.es")

    def button(d, _l, y=y):
        fb = dm(44, 700)
        bw = d.textlength(btn, font=fb)
        bx = (W - bw) / 2
        d.rounded_rectangle([bx - 52, y, bx + bw + 52, y + 112], radius=56, fill=LIME)
        d.text((bx, y + 29), btn, font=fb, fill=TEAL)
    sc.add(button, t + 0.2, "scale")
    return sc, t + 0.2


BUILD = {"cover": scene_cover, "point": scene_point, "stat": scene_stat, "cta": scene_cta}


def scene_duration(s, t_last):
    words = sum(len(str(s.get(k, "")).split()) for k in ("kicker", "title", "subtitle", "body", "value", "label", "note", "button"))
    read = 0.8 + words / 4.2  # lectura rápida en Reels
    return round(max(t_last + 0.6 + read, 3.0), 2)


def progress(img, i, n, t, dur, dark=True):
    d = ImageDraw.Draw(img)
    base = (80, 102, 102) if dark else (214, 220, 208)
    gap, top = 12, 120
    seg = (W - 2 * M - gap * (n - 1)) / n
    for k in range(n):
        x0 = M + k * (seg + gap)
        d.rounded_rectangle([x0, top, x0 + seg, top + 8], radius=4, fill=base)
        fill = 1.0 if k < i else (min(t / dur, 1.0) if k == i else 0)
        if fill > 0:
            d.rounded_rectangle([x0, top, x0 + seg * fill, top + 8], radius=4, fill=LIME)


def encode(frames_iter, out, dur):
    tmp = str(out) + ".tmp.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-profile:v", "high", "-r", str(FPS), "-t", str(dur), tmp]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in frames_iter:
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg falló")
    os.replace(tmp, out)


def render(folder, preview=False):
    folder = Path(folder)
    spec = json.loads((folder / "post.json").read_text(encoding="utf-8"))
    scenes = spec["scenes"]
    built = []
    for s in scenes:
        sc, t_last = BUILD[s["type"]](s)
        built.append((sc, scene_duration(s, t_last)))
    if preview:
        for i, (sc, dur) in enumerate(built, 1):
            img = sc.frame(dur)
            progress(img, i - 1, len(built), dur, dur, sc.dark)
            img.save(folder / f"preview_{i:02d}.jpg", quality=88)
        print(f"{folder}: {len(built)} previews")
        return
    with tempfile.TemporaryDirectory() as td:
        parts = []
        for i, (sc, dur) in enumerate(built):
            nfr = int(dur * FPS)

            def frames(sc=sc, i=i, dur=dur, nfr=nfr):
                for k in range(nfr):
                    t = k / FPS
                    img = sc.frame(t)
                    progress(img, i, len(built), t, dur, sc.dark)
                    # fundido rápido de entrada en cada escena
                    if t < 0.15 and i > 0:
                        img = Image.blend(Image.new("RGB", (W, H), TEAL), img, t / 0.15)
                    yield img
            part = Path(td) / f"s{i:02d}.mp4"
            encode(frames(), part, nfr / FPS)
            parts.append(part)
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        total = sum(d for _, d in built)
        tmp = folder / "reel.tmp.mp4"
        # vídeo + pista de audio silenciosa AAC (Instagram la espera)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest",
                        "-movflags", "+faststart", str(tmp)], check=True)
        os.replace(tmp, folder / "reel.mp4")
    # portada: último fotograma de la primera escena
    sc, dur = built[0]
    sc.frame(dur).save(folder / "cover.jpg", quality=92)
    spec["video"] = "reel.mp4"
    spec["cover"] = "cover.jpg"
    spec["duration"] = round(sum(d for _, d in built), 1)
    (folder / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{folder}: reel.mp4 ({spec['duration']} s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for a in args:
        render(a, preview="--preview" in sys.argv)
