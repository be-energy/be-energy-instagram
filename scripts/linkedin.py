#!/usr/bin/env python3
"""Publicación en el perfil personal de LinkedIn (Beatriz) con la API de LinkedIn.

post.json de un post de LinkedIn (carpeta en queue/):
  {"kind": "linkedin", "publish_at": "...", "topic": "...", "approved": false,
   "text": "Texto del post...\n\n#ahorroenergetico",
   "images": ["01.jpg", ...]}        # opcional: 1 imagen o varias (multi-imagen)
Solo se publica si "approved": true.

Variables: LINKEDIN_TOKEN (secreto), LINKEDIN_VERSION (AAAAMM, opcional).
"""
import json
import os
import re
import urllib.error
import urllib.request

TOKEN = os.environ.get("LINKEDIN_TOKEN", "").strip()
VERSION = os.environ.get("LINKEDIN_VERSION", "202606")


def _req(method, url, body=None, headers=None, raw=None):
    h = {"Authorization": f"Bearer {TOKEN}", "LinkedIn-Version": VERSION, "X-Restli-Protocol-Version": "2.0.0"}
    h.update(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            txt = r.read().decode() or "{}"
            return json.loads(txt) if txt.strip().startswith("{") else {}, dict(r.headers)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LinkedIn {e.code} en {url}: {e.read().decode(errors='replace')}") from None


def me():
    data, _ = _req("GET", "https://api.linkedin.com/v2/userinfo")
    return f"urn:li:person:{data['sub']}", data.get("name", "?")


RESERVED = r"\|{}@[]()<>*_~"


def little_text(text):
    """Escapa el texto al formato de LinkedIn y convierte #hashtags en hashtags reales."""
    out = []
    for token in re.split(r"(#[\wáéíóúüñÁÉÍÓÚÜÑ]+)", text):
        if token.startswith("#") and len(token) > 1:
            out.append("{hashtag|\\#|" + token[1:] + "}")
        else:
            out.append("".join("\\" + c if c in RESERVED or c == "#" else c for c in token))
    return "".join(out)


def upload_image(owner, path):
    init, _ = _req("POST", "https://api.linkedin.com/rest/images?action=initializeUpload",
                   {"initializeUploadRequest": {"owner": owner}})
    val = init["value"]
    up = urllib.request.Request(val["uploadUrl"], data=path.read_bytes(), method="PUT",
                                headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(up, timeout=120):
        pass
    return val["image"]


def check():
    owner, name = me()
    print(f"LinkedIn: {name} ({owner})")
    # comprueba también que la API de imágenes responde (no publica nada)
    _req("POST", "https://api.linkedin.com/rest/images?action=initializeUpload",
         {"initializeUploadRequest": {"owner": owner}})
    print("LinkedIn OK")


def publish(folder, spec, dry_run=False):
    owner, name = me()
    imgs = [folder / n for n in spec.get("images", [])]
    ids = [upload_image(owner, p) for p in imgs]
    body = {
        "author": owner,
        "commentary": little_text(spec["text"]),
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED", "targetEntities": [], "thirdPartyDistributionChannels": []},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if len(ids) == 1:
        body["content"] = {"media": {"id": ids[0], "altText": spec.get("topic", "")[:120]}}
    elif len(ids) > 1:
        body["content"] = {"multiImage": {"images": [{"id": i, "altText": ""} for i in ids[:20]]}}
    if dry_run:
        print(f"PRUEBA OK {folder.name}: {len(ids)} imagen(es) subidas, post listo para {name} (no se publica)")
        return None
    _, headers = _req("POST", "https://api.linkedin.com/rest/posts", body)
    urn = headers.get("x-restli-id") or headers.get("X-RestLi-Id", "")
    return {"media_id": urn, "permalink": f"https://www.linkedin.com/feed/update/{urn}/" if urn else ""}
