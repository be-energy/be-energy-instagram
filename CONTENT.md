# Guía editorial y procedimiento semanal — Instagram @beenergy.es

Este archivo lo lee el agente cada semana antes de crear contenido. Si Gerardo corrige algo, se actualiza aquí.

## Quiénes somos
be-energy (be-energy.es) audita contratos de luz de **comunidades de propietarios y empresas**: analiza la curva de consumo cuarto-horaria, ajusta la potencia contratada (tarifas 2.0TD / 3.0TD) y compara ofertas del mercado para que el cliente pague menos.

## Público
1. Administradores de fincas (principal).
2. Presidentes y vecinos de comunidades de propietarios.
3. Dueños y gerentes de pymes (comercios, oficinas, naves, hostelería).

## Reglas que no se rompen
- be-energy **no es una comercializadora**. Nunca presentarla como tal ni como marca de una tarifa.
- **No ofrecer asistir a juntas de vecinos** (ni en persona ni por videollamada).
- **No inventar casos, clientes, testimonios ni cifras de ahorro.** Los casos reales solo si Gerardo los aporta (en `ideas.md`), y siempre anonimizados.
- Nada de precios concretos de €/kW o €/kWh salvo que estén verificados ese mismo día con fuente oficial (BOE/CNMC). Mejor explicar conceptos que dar precios que caducan.
- Datos regulatorios correctos: 2.0TD hasta 15 kW (2 periodos de potencia, 3 de energía); 3.0TD más de 15 kW en baja tensión (6 y 6); en 3.0TD hay penalización por excesos de potencia; en 3.0TD las potencias deben ir de P1 a P6 en orden no decreciente.
- Tono: cercano, claro, sin tecnicismos innecesarios, tuteando. Español de España.
- CTA siempre hacia el **estudio gratuito** en be-energy.es (enlace en la bio).

## Pilares de contenido (rotar)
1. **Errores en la factura/contrato**: potencia sobredimensionada, tarifa que no encaja, reactiva, excesos…
2. **Explicaciones sencillas**: qué es la potencia, periodos, 2.0TD vs 3.0TD, curva cuarto-horaria, cómo leer la factura, maxímetro, energía reactiva…
3. **Para administradores de fincas**: cómo presentar el ahorro en junta, qué documentación pedir, checklist anual del contrato, cómo detectar comunidades con margen.
4. **Para empresas**: horarios de consumo y periodos, picos de arranque, potencia por periodo.
5. **Datos y curiosidades** (post de una imagen tipo `stat`).
6. **Casos reales** (solo con datos de Gerardo, tipo `compare`).

## Formato y calendario semanal (Europe/Madrid)
- **Feed:** 3 posts, **lunes, miércoles y viernes a las 10:00**.
- **Reel animado:** 1, **jueves a las 10:00** (`kind: "reel"`, 20–35 s, 4–6 escenas cortas).
- **Historias:** el mismo día de cada post del feed a las 10:30, un aviso "Nuevo post" (`story` tipo `teaser`), y el **martes a las 13:00** un "Consejo rápido" (`story` tipo `slide`).
- Mezcla semanal recomendada: 2 carruseles (portada + 3–5 puntos + CTA) y 1 imagen suelta (`stat`) o un `compare`.
- Copy: gancho en la primera línea, 3–6 líneas con emojis moderados, CTA y 6–10 hashtags.
- Hashtags base: #ahorroenergetico #facturadelaluz #comunidaddepropietarios #administradordefincas #eficienciaenergetica #potenciacontratada #empresas

## Procedimiento semanal (agente)
1. Leer este archivo, `ideas.md` (si tiene ideas pendientes, usarlas primero) y `published/LOG.md` + `queue/` para no repetir temas.
2. Crear las carpetas de la semana en `queue/` (3 posts de feed, 1 reel y 4 historias; en el ejemplo de abajo, los posts de feed) con nombre `AAAA-MM-DD-tema` para el lunes, miércoles y viernes siguientes, cada una con `post.json`:
   ```json
   {"publish_at": "2026-11-30T10:00:00+01:00", "topic": "...", "caption": "...",
    "slides": [{"type": "cover", "kicker": "...", "title": "... *resaltado* ...", "subtitle": "..."},
               {"type": "point", "n": 1, "title": "...", "body": "..."},
               {"type": "cta", "title": "¿Pagas de más en tu *luz?*", "body": "...", "button": "Estudio gratuito · be-energy.es"}]}
   ```
   Tipos de diapositiva de feed: `cover`, `point`, `stat` (value, label, note, kicker), `compare` (title, rows=[[concepto, antes, después]], note), `cta`. Las palabras entre `*asteriscos*` se resaltan. Para que dos palabras no se separen de línea, unirlas con espacio duro (U+00A0).
   Ojo con el horario: +01:00 en invierno, +02:00 entre el último domingo de marzo y el último de octubre.
   Reel (`kind: "reel"`): `{"kind":"reel","publish_at":"...","topic":"...","caption":"...","scenes":[cover, point…, cta]}`. Textos MUY cortos (títulos de 2–5 palabras, cuerpo de 1 frase); la duración se calcula sola.
   Historia: `{"kind":"story","publish_at":"...","topic":"...","story":{"type":"teaser","source":"<carpeta del post del feed>"}}` o `{"kind":"story",...,"story":{"type":"slide","label":"Consejo rápido","slide":{diapositiva point/stat}}}`. Las historias no llevan caption.
3. Renderizar: `python scripts/render.py queue/<carpeta>` (feed), `python scripts/render_reel.py queue/<carpeta>` (reel; con `--preview` saca solo fotogramas finales para revisar rápido) y `python scripts/render_story.py queue/<carpeta>` (historia; renderizar primero el post del feed al que apunta) y **revisar visualmente cada imagen** (texto cortado, líneas huérfanas, solapes). Corregir el texto y volver a renderizar si hace falta.
4. Commit y push a `main`. GitHub Actions publica solo a la hora indicada.
5. Enviar a Gerardo un resumen con las imágenes. Si quiere cambiar o cancelar un post, basta con editar o borrar su carpeta de `queue/` antes de la hora.
