#!/usr/bin/env python3
"""Publica en Instagram los posts de queue/ cuya fecha ya ha llegado.

Variables de entorno:
  META_TOKEN   token del usuario del sistema de Meta (secreto del repo)
  GITHUB_REPOSITORY  owner/repo (lo pone GitHub Actions)
  RAW_BRANCH   rama desde la que Instagram descarga las imágenes (por defecto main)
  FORCE_POST   nombre de carpeta en queue/ para publicarla ya, ignorando la fecha
  CHECK_ONLY   "1" para solo comprobar la conexión con Instagram

Cada carpeta de queue/ tiene post.json (kind: feed|reel|story, publish_at, ...) y sus archivos.
  DRY_RUN      "1" para crear el contenedor en Instagram sin publicarlo (prueba)
Al publicarse, la carpeta se mueve a published/ con el id del post de Instagram.
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://graph.facebook.com/" + os.environ.get("GRAPH_VERSION", "v23.0")
TOKEN = os.environ.get("META_TOKEN", "").strip()


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise RuntimeError(f"Error {e.code} en {path}: {body}") from None


def ig_account():
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"], "?"
    res = call("GET", "me/accounts", fields="name,instagram_business_account{id,username}")
    for page in res.get("data", []):
        ig = page.get("instagram_business_account")
        if ig:
            return ig["id"], ig.get("username", "?")
    raise RuntimeError("El token no ve ninguna página con Instagram vinculado: " + json.dumps(res))


def wait_ready(container_id, tries=60, every=5):
    for _ in range(tries):
        res = call("GET", container_id, fields="status_code,status")
        st = res.get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Contenedor {container_id} en estado {st}: {res.get('status')}")
        time.sleep(every)
    raise RuntimeError(f"Contenedor {container_id} no terminó a tiempo")


def upload_video(ig_id, path, **params):
    """Sube un vídeo con la subida reanudable de Meta (no depende de URLs públicas)."""
    c = call("POST", f"{ig_id}/media", upload_type="resumable", **params)
    cid = c["id"]
    data = path.read_bytes()
    req = urllib.request.Request(
        f"https://rupload.facebook.com/ig-api-upload/{API.rsplit('/', 1)[1]}/{cid}", data=data, method="POST",
        headers={"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(len(data))})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Error {e.code} subiendo vídeo: {e.read().decode(errors='replace')}") from None
    return cid


def raw_base(folder):
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ.get("RAW_BRANCH", "main")
    return f"https://raw.githubusercontent.com/{repo}/{branch}/queue/{urllib.parse.quote(folder.name)}/"


def build_container(ig_id, folder, spec):
    kind = spec.get("kind", "feed")
    base = raw_base(folder)
    if kind == "reel":
        params = {"media_type": "REELS", "caption": spec["caption"], "share_to_feed": "true"}
        if spec.get("cover"):
            params["cover_url"] = base + spec["cover"]
        c = upload_video(ig_id, folder / spec.get("video", "reel.mp4"), **params)
        wait_ready(c, tries=90, every=10)
        return c
    if kind == "story":
        c = call("POST", f"{ig_id}/media", media_type="STORIES", image_url=base + spec.get("images", ["story.jpg"])[0])["id"]
        wait_ready(c)
        return c
    images = spec.get("images") or sorted(p.name for p in folder.glob("*.jpg"))
    urls = [base + name for name in images]
    if len(urls) == 1:
        c = call("POST", f"{ig_id}/media", image_url=urls[0], caption=spec["caption"])["id"]
    else:
        children = []
        for u in urls[:10]:
            cid = call("POST", f"{ig_id}/media", image_url=u, is_carousel_item="true")["id"]
            wait_ready(cid)
            children.append(cid)
        c = call("POST", f"{ig_id}/media", media_type="CAROUSEL", children=",".join(children), caption=spec["caption"])["id"]
    wait_ready(c)
    return c


def publish(ig_id, folder, dry_run=False):
    spec = json.loads((folder / "post.json").read_text(encoding="utf-8"))
    c = build_container(ig_id, folder, spec)
    if dry_run:
        print(f"PRUEBA OK {folder.name}: contenedor {c} listo (no se publica)")
        return
    media_id = call("POST", f"{ig_id}/media_publish", creation_id=c)["id"]
    try:
        link = call("GET", media_id, fields="permalink").get("permalink", "")
    except Exception:
        link = ""
    spec["published"] = {"at": datetime.now(timezone.utc).isoformat(), "media_id": media_id, "permalink": link}
    (folder / "post.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    dest = ROOT / "published" / folder.name
    dest.parent.mkdir(exist_ok=True)
    shutil.move(str(folder), str(dest))
    with open(ROOT / "published" / "LOG.md", "a", encoding="utf-8") as f:
        f.write(f"- {spec['published']['at'][:16]} · {spec.get('kind', 'feed')} · {folder.name} · {spec.get('topic', '')} · {link}\n")
    print(f"PUBLICADO {folder.name} -> {link or media_id}")


def main():
    if not TOKEN:
        sys.exit("Falta el secreto META_TOKEN")
    ig_id, user = ig_account()
    print(f"Cuenta de Instagram: @{user} ({ig_id})")
    if os.environ.get("CHECK_ONLY") == "1":
        print("Conexión OK")
        return
    now = datetime.now(timezone.utc)
    force = os.environ.get("FORCE_POST", "").strip()
    dry = os.environ.get("DRY_RUN") == "1"
    errors = 0
    for folder in sorted((ROOT / "queue").iterdir()):
        pj = folder / "post.json"
        if not pj.is_file():
            continue
        spec = json.loads(pj.read_text(encoding="utf-8"))
        due = datetime.fromisoformat(spec["publish_at"]) <= now
        if (force and folder.name == force) or (not force and due):
            try:
                publish(ig_id, folder, dry_run=dry)
            except Exception as e:
                errors += 1
                print(f"ERROR publicando {folder.name}: {e}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
