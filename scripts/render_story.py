#!/usr/bin/env python3
"""Genera una historia (story) 1080x1920 JPEG a partir de post.json.

Uso:  python scripts/render_story.py queue/2026-11-23-story-senales

post.json de una historia:
  {"kind": "story", "publish_at": "...", "topic": "...",
   "story": {"type": "teaser", "source": "2026-11-23-senales-potencia"}}
      -> portada de un post del feed con la etiqueta "Nuevo post"
  {"kind": "story", "publish_at": "...", "topic": "...",
   "story": {"type": "slide", "label": "Consejo rápido", "slide": {<diapositiva point/stat/compare>}}}
      -> una diapositiva suelta enmarcada para historias
Escribe story.jpg en la carpeta.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render import GREY_L, LIME, RENDER, ROOT, TEAL, dm  # noqa: E402

W, H = 1080, 1920


def frame(inner, label, footer):
    img = Image.new("RGB", (W, H), TEAL)
    d = ImageDraw.Draw(img)
    d.ellipse([W - 260, -260, W + 260, 260], outline=LIME, width=18)
    # tarjeta centrada con esquinas redondeadas
    cw = 940
    ch = int(inner.height * cw / inner.width)
    card = inner.resize((cw, ch), Image.LANCZOS)
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, cw, ch], radius=36, fill=255)
    top = (H - ch) // 2 + 40
    img.paste(card, ((W - cw) // 2, top), mask)
    d.rounded_rectangle([(W - cw) // 2 - 8, top - 8, (W + cw) // 2 + 8, top + ch + 8], radius=44, outline=LIME, width=6)
    f = dm(36, 700)
    lab = label.upper()
    tw = d.textlength(lab, font=f)
    d.rounded_rectangle([(W - tw) / 2 - 30, top - 110, (W + tw) / 2 + 30, top - 36], radius=37, fill=LIME)
    d.text(((W - tw) / 2, top - 96), lab, font=f, fill=TEAL)
    f2 = dm(38, 500)
    tw2 = d.textlength(footer, font=f2)
    d.text(((W - tw2) / 2, top + ch + 50), footer, font=f2, fill=GREY_L)
    return img


def render(folder):
    folder = Path(folder)
    spec = json.loads((folder / "post.json").read_text(encoding="utf-8"))
    st = spec["story"]
    if st["type"] == "teaser":
        src = None
        for base in ("queue", "published"):
            p = ROOT / base / st["source"] / "01.jpg"
            if p.exists():
                src = p
                break
        if not src:
            raise SystemExit(f"No encuentro la portada de {st['source']}")
        img = frame(Image.open(src).convert("RGB"), st.get("label", "Nuevo post"),
                    st.get("footer", "Míralo completo en nuestro perfil"))
    else:
        inner = RENDER[st["slide"]["type"]](st["slide"], 1, 1)
        img = frame(inner, st.get("label", "Consejo rápido"), st.get("footer", "Estudio gratuito en be-energy.es"))
    img.save(folder / "story.jpg", "JPEG", quality=92, optimize=True)
    spec["images"] = ["story.jpg"]
    (folder / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{folder}: story.jpg")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        render(a)
