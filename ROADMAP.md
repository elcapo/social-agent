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

### Fase 8 — Soporte de imágenes en publicaciones
- [x] Extender modelo `Draft` con `media_urls` y `media_paths`
- [x] Añadir Pillow a dependencias
- [x] Módulo `media.py` para procesamiento de imágenes
- [x] TwitterPublisher con subida de medios (v1.1 API)
- [x] LinkedInPublisher con subida de imágenes (v2 REST)
- [x] Endpoint `POST /api/drafts/{id}/attach-media`
- [x] CLI con flag `--media-url`
- [x] Frontend con input de URLs y upload de archivos
- [x] Tests

---

## Fase 9 — Revisión UI: componentes nativos de DaisyUI

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

### Fase 9 — Revisión UI: componentes nativos de DaisyUI
- [x] Instalar skill oficial de DaisyUI
- [x] Auditar frontend: Layout, Nav, index.astro, sources.astro, seeds.astro, drafts.astro
- [x] Layout.astro: eliminar Google Fonts + CSS manual de fonts; body con clases DaisyUI/Tailwind (`bg-base-100 text-base-content font-sans`)
- [x] index.astro: loaders con `<span class="loading loading-spinner">`; empty states con `<div class="alert">`
- [x] sources.astro: loaders con `<span class="loading loading-spinner">`; empty states con `<div class="alert">`
- [x] seeds.astro: loaders con `<span class="loading loading-spinner">`; empty states con `<div class="alert">`
- [x] drafts.astro: loaders con `<span class="loading loading-spinner">`; empty states con `<div class="alert">`
- [x] Build exitoso — verificado

## Fase 10 — Programación de publicaciones

### Contexto

Actualmente los publishers publican de forma inmediata al invocar el comando o endpoint correspondiente. No existe la posibilidad de programar una publicación para una fecha futura, algo esencial para la gestión de redes sociales.

### Plan de implementación

#### 10.1 Extender el modelo `Draft`

- Añadir campo opcional `scheduled_at: datetime | None = None` a `Draft`
- Incluirlo en `to_frontmatter()` y `from_frontmatter()` para persistencia
- Al serializar a frontmatter, convertirlo a string ISO 8601
- Al deserializar, parsear el string ISO 8601 con `datetime.fromisoformat()`

#### 10.2 Añadir scheduler a la base de datos de drafts

- En `MarkdownStore`, al guardar un draft con `scheduled_at` poblado, el draft se persiste con estado `draft` (no se publica aún)
- Crear método `list_scheduled(since: datetime | None = None) -> list[Draft]` que devuelva drafts con `scheduled_at <= now` y `status == DraftStatus.DRAFT`

#### 10.3 Crear comando CLI `schedule`

- `social-agent schedule publish` — busca drafts con `scheduled_at <= now` y los publica
- `social-agent schedule list` — lista drafts programados (futuros)
- `social-agent schedule cancel <id>` — elimina el `scheduled_at` de un draft

#### 10.4 Añadir endpoints API REST

- `GET /api/drafts/scheduled` — lista drafts programados
- `POST /api/drafts/{id}/schedule` — establece `scheduled_at` en el draft
- `POST /api/scheduler/run` — ejecuta el scheduler (publica drafts pendientes)
- `POST /api/drafts/{id}/unschedule` — elimina la programación

#### 10.5 Crear worker de scheduler (background)

- Implementar `backend/src/social_agent/scheduler.py` con un loop simple o usando `asyncio`
- Configurar intervalo de verificación configurable (ej. cada 5 minutos)
- Opcional: integrar con `APScheduler` o similar si se quiere persistencia de jobs

#### 10.6 Actualizar frontend (Astro)

- En vista de drafts, mostrar indicador visual cuando un draft está programado (icono de calendario + fecha)
- Añadir campo de fecha/hora en el formulario de creación/edición de drafts
- Añadir sección "Programados" en el dashboard

#### 10.7 Tests

- Tests unitarios para `scheduled_at` en Draft (serialización/deserialización)
- Tests para `list_scheduled()` en MarkdownStore
- Tests para los nuevos endpoints de scheduler
- Tests del comando CLI `schedule`

### Fase 10 — Programación de publicaciones
- [x] Extender modelo `Draft` con `scheduled_at: datetime | None` + serialización ISO 8601
- [x] `MarkdownStore.list_scheduled(since, status_value)` para drafts due
- [x] Módulo `scheduler.py` con `run_once()` y `run_loop()` (worker async)
- [x] Comandos CLI `schedule set/list/cancel/publish/worker`
- [x] Endpoints API: `GET /api/drafts/scheduled`, `POST /api/drafts/{id}/schedule`, `POST /api/drafts/{id}/unschedule`, `POST /api/scheduler/run`
- [x] Frontend: indicador de calendario en lista de drafts, campo datetime en edición, sección "Scheduled Drafts" en dashboard con botón "Run scheduler"
- [x] Tests — 225 tests, todos pasan (45 nuevos)

## Fase 11 — Migración a base de datos (SQLite + patrón repositorio)

### Contexto

Actualmente toda la persistencia se basa en archivos Markdown con frontmatter YAML. Si bien es funcional para un proyecto pequeño, esta aproximación presenta limitaciones:
- Consultas complejas (filtros múltiples, ordenaciones) requieren cargar y parsear todos los archivos
- Sin integridad referencial ni transacciones
- Escalabilidad limitada

Se propone migrar a SQLite como base de datos ligera y embebida, aplicando el **patrón repositorio** para abstraer la capa de persistencia y facilitar futuras migraciones a otros motores (PostgreSQL, MySQL, etc.).

### Plan de implementación

#### 11.1 Elección de tecnología

- **Base de datos:** SQLite (vía `aiosqlite` + `SQLAlchemy` para async)
- **ORM/SQL:** SQLAlchemy 2.0 con modo `async` y `declarative mapping`
- **Migraciones:** Alembic para control de versiones del esquema
- **Patrón:** Repository Pattern con interfaces abstractas

#### 11.2 Definir el esquema de base de datos

- Tabla `sources` → equivalente a `Source` (id, type, name, url, priority, active, created_at, updated_at)
- Tabla `seeds` → equivalente a `Seed` (id, source_id FK, content, status, interests, created_at, updated_at)
- Tabla `drafts` → equivalente a `Draft` (id, seed_id FK, platform, content, status, scheduled_at, media_urls JSON, created_at, updated_at)
- Tabla `published` → historial de publicaciones (id, draft_id FK, platform, post_url, published_at)
- Usar `UUID` como Primary Key o `Integer` autoincremental (decidir en implementación)
- Índices apropiados para búsquedas frecuentes (status, platform, scheduled_at, created_at)

#### 11.3 Definir interfaces de repositorio

Crear `backend/src/social_agent/storage/repositories/` con:

- `base.py` — `ABC` con métodos CRUD genéricos (`get`, `list`, `create`, `update`, `delete`)
- `source_repository.py` — `SourceRepository` con métodos específicos (`list_active`, `find_by_type`)
- `seed_repository.py` — `SeedRepository` con métodos específicos (`list_by_status`, `list_by_source`)
- `draft_repository.py` — `DraftRepository` con métodos específicos (`list_scheduled`, `list_by_platform`, `list_by_status`)

Cada repositorio define una interfaz abstracta (`Protocol` o `ABC`) que cualquier implementación concreta debe cumplir.

#### 11.4 Implementar repositorio SQLite con SQLAlchemy

- `sqlalchemy_repository.py` — Implementación concreta de cada repositorio usando SQLAlchemy async sessions
- Manejo de sesiones con `async_sessionmaker`
- Mapeo de modelos ORM a modelos Pydantic del dominio
- Manejo de `media_urls` como JSON en SQLite

#### 11.5 Mantener `MarkdownStore` como implementación alternativa (opcional)

- Para desarrollo local y simplicidad, mantener `MarkdownStore` pero adaptarlo a la misma interfaz de repositorio
- Permitir cambiar entre implementaciones vía configuración (`config.py`)

#### 11.6 Configurar Alembic

- `alembic init alembic` en `backend/`
- Configurar `alembic.ini` con `sqlalchemy.url`
- Crear migración inicial con todas las tablas
- Script de `seed` para datos iniciales (si aplica)

#### 11.7 Actualizar dependencias

- Añadir `sqlalchemy>=2.0`, `aiosqlite`, `alembic` a `pyproject.toml`
- Opcional: `alembic-utils` para migraciones más complejas

#### 11.8 Migrar la lógica de negocio

- Actualizar `MarkdownStore` o crear nuevo `DatabaseStore` que use los repositorios
- Los agentes (`ideator.py`, `writer.py`) y publishers deben recibir el repositorio por inyección de dependencias
- Actualizar routers de FastAPI para usar los nuevos repositorios (vía `Depends`)
- Actualizar comandos CLI para usar los nuevos repositorios

#### 11.9 Estrategia de migración de datos

- Script `migrate_to_sqlite.py` que lea todos los archivos Markdown existentes y los inserte en SQLite
- Preservar IDs si es posible, o mantener un mapeo
- Ejecutar como comando CLI `social-agent db migrate`

#### 11.10 Tests

- Tests unitarios para cada repositorio (usando SQLite en memoria)
- Tests de integración con la base de datos real
- Tests de la migración de datos
- Verificar que todos los tests existentes siguen pasando (los de `MarkdownStore` deben coexistir)

---

### Notas técnicas

| Plataforma | API de media upload | Límite de imágenes | Formato |
|---|---|---|---|
| Twitter | `POST media/upload` (v1.1) + `media_ids` en create_tweet (v2) | 4 imágenes | PNG, JPEG, GIF, WEBP ≤ 5 MB |
| LinkedIn | `POST /rest/images` → `PUT` upload URL → incluir URN en post | 1 imagen por post | JPEG, PNG, GIF ≤ 10 MB |
