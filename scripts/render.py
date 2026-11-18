#!/usr/bin/env python3
"""Renderiza las diapositivas de un post de be-energy a JPEG 1080x1350.

Uso:  python scripts/render.py queue/2026-11-23-potencia
Lee post.json de esa carpeta y escribe 01.jpg, 02.jpg, ...

Tipos de diapositiva (campo "type"):
  cover    -> portada oscura: kicker, title, subtitle
  point    -> fondo claro: n, title, body
  stat     -> cifra grande: value, label, note
  compare  -> antes/después: title, rows=[[concepto, antes, despues], ...], note
  cta      -> cierre: title, body, button
En title/body, las palabras entre *asteriscos* se resaltan en verde.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
W, H = 1080, 1350
M = 96  # margen

TEAL = (45, 64, 64)
TEAL_2 = (58, 80, 80)
LIME = (175, 203, 55)
LIGHT = (243, 245, 238)
WHITE = (255, 255, 255)
GREY_L = (200, 212, 208)
GREY_D = (90, 105, 105)


def bebas(size):
    return ImageFont.truetype(str(FONTS / "BebasNeue-Regular.ttf"), size)


def dm(size, weight=400):
    f = ImageFont.truetype(str(FONTS / "DMSans-VF.ttf"), size)
    try:
        f.set_variation_by_axes([min(max(size * 0.75, 9), 40), weight])
    except Exception:
        pass
    return f


def tokens(text):
    """Divide en palabras marcando las resaltadas con *...*."""
    out, hl = [], False
    for raw in text.replace("\n", " \n ").split(" "):
        if raw == "":
            continue
        if raw == "\n":
            out.append(("\n", False))
            continue
        w = raw
        start = w.startswith("*")
        if start:
            hl = True
            w = w[1:]
        end = w.endswith("*") or w.endswith("*,") or w.endswith("*.") or w.endswith("*:") or w.endswith("*?") or w.endswith("*!")
        if end:
            i = w.rfind("*")
            w = w[:i] + w[i + 1:]
        out.append((w, hl))
        if end:
            hl = False
    return out


def wrap(draw, text, font, maxw):
    lines, cur, curw = [], [], 0
    space = draw.textlength(" ", font=font)
    for w, hl in tokens(text):
        if w == "\n":
            lines.append(cur)
            cur, curw = [], 0
            continue
        ww = draw.textlength(w, font=font)
        add = ww if not cur else space + ww
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [(w, hl)], ww
        else:
            cur.append((w, hl))
            curw += add
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, fontfn, maxw, maxh, sizes, lh=1.0):
    for s in sizes:
        f = fontfn(s)
        lines = wrap(draw, text, f, maxw)
        if len(lines) * s * lh <= maxh:
            return f, lines, s
    f = fontfn(sizes[-1])
    return f, wrap(draw, text, f, maxw), sizes[-1]


def draw_lines(draw, lines, font, x, y, size, color, hl_color, lh=1.0, marker=None, align="left", maxw=None):
    space = draw.textlength(" ", font=font)
    for line in lines:
        lw = sum(draw.textlength(w, font=font) for w, _ in line) + space * max(len(line) - 1, 0)
        cx = x if align == "left" else x + (maxw - lw) / 2
        pos = []
        for w, hl in line:
            ww = draw.textlength(w, font=font)
            pos.append((cx, ww, w, hl))
            cx += ww + space
        if marker:
            i = 0
            while i < len(pos):
                if pos[i][3]:
                    j = i
                    while j + 1 < len(pos) and pos[j + 1][3]:
                        j += 1
                    draw.rectangle([pos[i][0] - 8, y + size * 0.48, pos[j][0] + pos[j][1] + 8, y + size * 0.9], fill=marker)
                    i = j + 1
                else:
                    i += 1
        for px, ww, w, hl in pos:
            draw.text((px, y), w, font=font, fill=(hl_color if hl else color))
        y += size * lh
    return y


def paste_logo(img, dark, width, xy):
    logo = Image.open(ROOT / "assets" / ("logo_dark.png" if dark else "logo_color.png")).convert("RGBA")
    r = width / logo.width
    logo = logo.resize((int(logo.width * r), int(logo.height * r)), Image.LANCZOS)
    img.paste(logo, (int(xy[0]), int(xy[1] - logo.height)), logo)


def footer(img, d, dark, idx, total, swipe):
    paste_logo(img, dark, 175, (M, H - 70))
    col = GREY_L if dark else GREY_D
    f = dm(30, 600)
    if total > 1:
        txt = "DESLIZA  →" if swipe else f"{idx}/{total}"
        tw = d.textlength(txt, font=f)
        d.text((W - M - tw, H - 70 - 34), txt, font=f, fill=(LIME if (dark and swipe) else col))


def centered(img, build, top=130, bottom=H - 230):
    """build(draw) dibuja desde y=0 en una capa y devuelve la altura usada; se centra en vertical."""
    layer = Image.new("RGBA", (W, H * 2), (0, 0, 0, 0))
    h = build(ImageDraw.Draw(layer))
    off = top + max((bottom - top - h) / 2, 0)
    img.paste(layer, (0, int(off)), layer)


def slide_cover(s, idx, total):
    img = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(img)
    # detalle gráfico: arco verde
    d.ellipse([W - 330, -330, W + 330, 330], outline=LIME, width=18)
    y = 210
    if s.get("kicker"):
        f = dm(30, 700)
        k = s["kicker"].upper()
        tw = d.textlength(k, font=f)
        d.rounded_rectangle([M, y, M + tw + 48, y + 62], radius=31, fill=LIME)
        d.text((M + 24, y + 13), k, font=f, fill=TEAL)
        y += 120
    f, lines, size = fit(d, s["title"], bebas, W - 2 * M, 640, range(170, 80, -6), 0.95)
    y = draw_lines(d, lines, f, M, y, size, WHITE, LIME, 0.95)
    if s.get("subtitle"):
        y += 30
        f2, l2, s2 = fit(d, s["subtitle"], lambda z: dm(z, 400), W - 2 * M, H - 220 - y, range(44, 28, -2), 1.35)
        draw_lines(d, l2, f2, M, y, s2, GREY_L, LIME, 1.35)
    footer(img, d, True, idx, total, swipe=total > 1)
    return img


def slide_point(s, idx, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d0 = ImageDraw.Draw(img)

    def build(d):
        y = 0
        if s.get("n") is not None:
            d.ellipse([M, y, M + 140, y + 140], fill=LIME)
            f = bebas(100)
            n = str(s["n"]).zfill(2)
            tw = d.textlength(n, font=f)
            d.text((M + 70 - tw / 2, y + 22), n, font=f, fill=TEAL)
            y += 200
        f, lines, size = fit(d, s["title"], bebas, W - 2 * M, 430, range(140, 70, -4), 0.98)
        y = draw_lines(d, lines, f, M, y, size, TEAL, TEAL, 0.98, marker=LIME)
        y += 30
        d.rectangle([M, y, M + 100, y + 9], fill=LIME)
        y += 55
        if s.get("body"):
            f2, l2, s2 = fit(d, s["body"], lambda z: dm(z, 450), W - 2 * M, 420, range(46, 30, -2), 1.38)
            y = draw_lines(d, l2, f2, M, y, s2, TEAL_2, TEAL, 1.38, marker=(220, 234, 160))
        return y

    centered(img, build)
    footer(img, d0, False, idx, total, swipe=False)
    return img


def slide_stat(s, idx, total):
    img = Image.new("RGB", (W, H), TEAL)
    d0 = ImageDraw.Draw(img)
    d0.ellipse([W - 330, -330, W + 330, 330], outline=LIME, width=18)

    def build(d):
        y = 0
        if s.get("kicker"):
            f = dm(36, 700)
            d.text((M, y), s["kicker"].upper(), font=f, fill=LIME)
            y += 90
        f, lines, size = fit(d, s["value"], bebas, W - 2 * M, 420, range(380, 120, -10), 0.9)
        y = draw_lines(d, lines, f, M, y, size, LIME, LIME, 0.9)
        y += 30
        f2, l2, s2 = fit(d, s.get("label", ""), lambda z: dm(z, 500), W - 2 * M, 330, range(60, 34, -2), 1.3)
        y = draw_lines(d, l2, f2, M, y, s2, WHITE, LIME, 1.3)
        if s.get("note"):
            y += 40
            d.rectangle([M, y, M + 100, y + 9], fill=LIME)
            y += 50
            f3, l3, s3 = fit(d, s["note"], lambda z: dm(z, 400), W - 2 * M, 260, range(40, 28, -2), 1.38)
            y = draw_lines(d, l3, f3, M, y, s3, GREY_L, LIME, 1.38)
        return y

    centered(img, build)
    footer(img, d0, True, idx, total, swipe=False)
    return img


def slide_compare(s, idx, total):
    img = Image.new("RGB", (W, H), LIGHT)
    d = ImageDraw.Draw(img)
    y = 170
    f, lines, size = fit(d, s["title"], bebas, W - 2 * M, 260, range(110, 60, -4), 0.98)
    y = draw_lines(d, lines, f, M, y, size, TEAL, TEAL, 0.98, marker=LIME) + 50
    cw = (W - 2 * M)
    c1, c2, c3 = M, M + cw * 0.46, M + cw * 0.73
    fh = dm(28, 700)
    d.text((c2, y), "ANTES", font=fh, fill=GREY_D)
    d.text((c3, y), "DESPUÉS", font=fh, fill=TEAL)
    y += 60
    fl, fv = dm(34, 500), bebas(64)
    for row in s.get("rows", []):
        label, before, after = row
        d.rounded_rectangle([M - 20, y - 14, W - M + 20, y + 96], radius=18, fill=WHITE)
        ll = wrap(d, label, fl, cw * 0.44)
        ly = y + 41 - 21 * len(ll)
        for line in ll:
            d.text((c1, ly), " ".join(w for w, _ in line), font=fl, fill=TEAL_2)
            ly += 42
        d.text((c2, y + 8), before, font=fv, fill=GREY_D)
        bw = d.textlength(before, font=fv)
        d.line([c2 - 4, y + 42, c2 + bw + 4, y + 42], fill=(200, 90, 80), width=4)
        d.rounded_rectangle([c3 - 14, y + 2, c3 + d.textlength(after, font=fv) + 14, y + 80], radius=12, fill=LIME)
        d.text((c3, y + 8), after, font=fv, fill=TEAL)
        y += 130
    if s.get("note"):
        y += 20
        f3, l3, s3 = fit(d, s["note"], lambda z: dm(z, 400), W - 2 * M, H - 200 - y, range(32, 22, -2), 1.35)
        draw_lines(d, l3, f3, M, y, s3, GREY_D, TEAL, 1.35)
    footer(img, d, False, idx, total, swipe=False)
    return img


def slide_cta(s, idx, total):
    img = Image.new("RGB", (W, H), TEAL)
    d0 = ImageDraw.Draw(img)
    d0.ellipse([-300, H - 420, 300, H + 180], outline=LIME, width=18)
    d0.ellipse([W - 260, -260, W + 260, 260], outline=LIME, width=18)
    logo = Image.open(ROOT / "assets" / "logo_dark.png").convert("RGBA")
    lw = 360
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)

    def build(d):
        y = 0
        d._image.paste(logo, (int((W - lw) / 2), y), logo)
        y += logo.height + 80
        f, lines, size = fit(d, s.get("title", "¿Pagas de más en tu luz?"), bebas, W - 2 * M, 330, range(140, 70, -4), 0.98)
        y = draw_lines(d, lines, f, M, y, size, WHITE, LIME, 0.98, align="center", maxw=W - 2 * M)
        y += 30
        if s.get("body"):
            f2, l2, s2 = fit(d, s["body"], lambda z: dm(z, 450), W - 2 * M, 220, range(46, 30, -2), 1.35)
            y = draw_lines(d, l2, f2, M, y, s2, GREY_L, LIME, 1.35, align="center", maxw=W - 2 * M)
        y += 60
        btn = s.get("button", "Estudio gratuito · be-energy.es")
        fb = dm(40, 700)
        bw = d.textlength(btn, font=fb)
        bx = (W - bw) / 2
        d.rounded_rectangle([bx - 48, y, bx + bw + 48, y + 104], radius=52, fill=LIME)
        d.text((bx, y + 27), btn, font=fb, fill=TEAL)
        return y + 104

    centered(img, build, top=120, bottom=H - 120)
    return img


RENDER = {"cover": slide_cover, "point": slide_point, "stat": slide_stat, "compare": slide_compare, "cta": slide_cta}


def render(post_dir):
    post_dir = Path(post_dir)
    spec = json.loads((post_dir / "post.json").read_text(encoding="utf-8"))
    slides = spec["slides"]
    for old in post_dir.glob("*.jpg"):
        old.unlink()
    out = []
    for i, s in enumerate(slides, 1):
        img = RENDER[s["type"]](s, i, len(slides))
        p = post_dir / f"{i:02d}.jpg"
        img.save(p, "JPEG", quality=92, optimize=True)
        out.append(p.name)
    spec["images"] = out
    (post_dir / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{post_dir}: {len(out)} imágenes")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        render(p)
