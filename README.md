# be-energy-instagram

Publicación automática del Instagram **@beenergy.es**.

- `queue/` → posts pendientes (una carpeta por post: `post.json` + imágenes JPG).
- `published/` → posts ya publicados y `LOG.md` con el enlace de cada uno.
- `scripts/render.py` → genera las imágenes con la marca be-energy.
- `scripts/publish.py` → publica en Instagram vía API de Meta.
- `.github/workflows/publish.yml` → se ejecuta cada hora y publica lo que toque.
- `CONTENT.md` → guía editorial y procedimiento semanal.
- `ideas.md` → apunta aquí ideas o casos reales para próximos posts.

**Cancelar o cambiar un post:** edita o borra su carpeta en `queue/` antes de la hora de publicación.

**Probar la conexión:** pestaña *Actions* → *Publicar en Instagram* → *Run workflow* → modo `comprobar`.

El token de Meta está en el secreto `META_TOKEN` del repositorio (Settings → Secrets and variables → Actions).
