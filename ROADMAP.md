# Roadmap

## Fases completadas

### Fase 1 — Base del proyecto
- [x] AGENTS.md
- [x] pyproject.toml + estructura de directorios
- [x] Modelos Pydantic (Source, Seed, Draft)
- [x] MarkdownStore (CRUD con frontmatter)
- [x] CLI base con Click (skeleton de comandos)
- [x] Tests unitarios (almacenamiento y modelos) — 19 tests, todos pasan
- [x] Verificar que tests pasan

### Fase 2 — Sistema de recolección e ideación
- [x] Sistema de prompts (interests + fuentes)
- [x] Collectors (RSS, web scraping, social) — RSSCollector, WebScraperCollector, TwitterCollector, LinkedInCollector
- [x] Ideator agent (LLM vía LiteLLM)
- [x] Tests — 27 tests, todos pasan

### Fase 3 — Writer y drafts multi-plataforma
- [x] Prompts de plataforma (Twitter, LinkedIn)
- [x] Writer agent (genera drafts)
- [x] Ciclo completo vía CLI
- [x] Tests — 34 tests, todos pasan

### Fase 4 — API REST
- [x] FastAPI con routers (sources, seeds, drafts, publish)
- [x] Tests de integración — 61 tests, todos pasan

### Fase 5 — Frontend Astro
- [x] Páginas básicas (dashboard, seeds, drafts)
- [x] Componentes (Layout, Nav)

### Fase 6 — Publicadores y APIs sociales
- [x] Twitter publisher (API v2 con Tweepy)
- [x] LinkedIn publisher (API Posts con httpx)
- [x] Social collectors (TwitterCollector funcional, LinkedInCollector implementado)
- [x] Tests — 81 tests, todos pasan

### Fase 7 — Extensibilidad, pulido, docs
- [x] Documentación de API
- [x] Guía para añadir plataformas
- [x] Tests finales

---

## Fase 8 — Soporte de imágenes en publicaciones

### Contexto

Actualmente los publishers de Twitter y LinkedIn solo publican texto. Ambas plataformas
soportan imágenes en sus APIs y las librerías del proyecto (Tweepy, httpx) lo permiten,
pero falta implementar la capa de media upload y extender el modelo `Draft`.

### Plan de implementación

#### 8.1 Extender el modelo `Draft`

- Añadir campo `media_urls: list[str] = []` a `Draft`
- Incluirlo en `to_frontmatter()` y `from_frontmatter()` para persistencia
- Añadir campo opcional `media_paths: list[str]` para rutas locales

#### 8.2 Añadir dependencia de procesamiento de imágenes

- Agregar `Pillow>=10.0` a `pyproject.toml`
- Validar formatos, tamaño máximo y redimensionar si es necesario antes de subir

#### 8.3 Actualizar `TwitterPublisher`

- En el `__init__`, añadir autenticación v1.1 (`tweepy.API` + `tweepy.OAuth1UserHandler`) además del `tweepy.Client` v2
- Crear método `_upload_media(ruta: str) -> int` que use `api.media_upload()` y devuelva el `media_id`
- Modificar `publish()` para que si `draft.media_urls` no está vacío:
  1. Descargue cada imagen a un archivo temporal
  2. Las suba con `api.media_upload()`
  3. Pase `media_ids=[...]` a `client.create_tweet()`

#### 8.4 Actualizar `LinkedInPublisher`

- Implementar flujo de subida:
  1. `POST /rest/images?action=initializeUpload` con `author` URN → obtiene `uploadUrl` y `image` URN
  2. Subir el binario de la imagen con `PUT` a la `uploadUrl`
  3. Incluir la image URN en el payload del post bajo `content.media`
- Soporte para una imagen por post (límite de la API de LinkedIn)

#### 8.5 Actualizar API REST

- Añadir endpoint `POST /api/drafts/{id}/attach-media` que acepte una URL o un upload de archivo
- Modificar `POST /api/publish/{id}` para propagar los medios al publisher

#### 8.6 Actualizar CLI

- Añadir flag `--media-url` (múltiple) al comando `publish`

#### 8.7 Actualizar frontend (Astro)

- Añadir campo de input de URLs de imágenes o selector de archivos en la vista de drafts
- Mostrar miniaturas de las imágenes adjuntas

#### 8.8 Tests

- Tests unitarios para el nuevo campo `media_urls` en Draft (serialización/deserialización)
- Tests de integración con mocking de las APIs de media upload
- Verificar que los publishers existentes siguen funcionando sin medios (backwards compatibility)

### Notas técnicas

| Plataforma | API de media upload | Límite de imágenes | Formato |
|---|---|---|---|
| Twitter | `POST media/upload` (v1.1) + `media_ids` en create_tweet (v2) | 4 imágenes | PNG, JPEG, GIF, WEBP ≤ 5 MB |
| LinkedIn | `POST /rest/images` → `PUT` upload URL → incluir URN en post | 1 imagen por post | JPEG, PNG, GIF ≤ 10 MB |
