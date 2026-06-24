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

### Decisiones de diseño (confirmadas)

| # | Decisión | Opción elegida | Razón |
|---|---|---|---|
| 1 | Primary Key | UUID v4 como `String(36)` con prefijos `draft_`/`idea_`/`seed_`/`src_` | Conserva los IDs existentes en Markdown y la legibilidad; evita colisiones en la migración |
| 2 | `MarkdownStore` | Se mantiene como backend alternativo seleccionable vía `config.py` (no se deprecata) | Los 225 tests existentes siguen pasando; permite dev/test sin BD |
| 3 | Async vs sync | **SQLAlchemy 2.0 sync** (diverge del plan original async) | Todo el codebase es síncrono (endpoints `def`, `httpx` sync, `MarkdownStore`, scheduler `run_once`). Async obligaría a refactorizar endpoints, publishers y tests. El patrón repositorio permite async futuro sin tocar lógica de negocio |
| 4 | Scheduler | Adaptar `run_once`/`run_loop` para recibir `DraftRepository` (Protocol) en vez de `MarkdownStore[Draft]` | Coherencia con el patrón repositorio; los callers construyen el repo vía factory |
| 5 | Modelo `Idea` | **Añadir tabla `ideas` + `IdeaRepository`** (gap del ROADMAP original) | El ROADMAP omitía `Idea`, pero el flujo `seed → idea → draft` y `router_ideas.py` dependen de él |

### Plan de implementación

#### 11.1 Elección de tecnología

- **Base de datos:** SQLite (vía `sqlite3` embebido + SQLAlchemy 2.0 **sync**)
- **ORM/SQL:** SQLAlchemy 2.0 con `declarative mapping` y sesiones síncronas (`sessionmaker`)
- **Migraciones:** Alembic para control de versiones del esquema
- **Patrón:** Repository Pattern con interfaces basadas en `Protocol` (structural typing)

#### 11.2 Definir el esquema de base de datos

- Tabla `sources` → equivalente a `Source` (id, name, source_type, url, priority, tags JSON, config JSON, enabled, created_at, last_fetched)
- Tabla `seeds` → equivalente a `Seed` (id, title, content, source_id FK→sources, source_url, source_name, tags JSON, status, created_at)
- Tabla `ideas` → equivalente a `Idea` (id, seed_id FK→seeds, title, summary, source_url, status, created_at) — **añadida (gap del ROADMAP original)**
- Tabla `drafts` → equivalente a `Draft` (id, idea_id FK→ideas, platform, content, status, notes, platform_post_id, publish_error, publish_attempts, media_urls JSON, media_paths JSON, created_at, published_at, scheduled_at)
- Tabla `published` → historial de publicaciones (id int autoincr, draft_id FK→drafts, platform, post_url, published_at)
- **Primary Key:** UUID v4 como `String(36)` (conserva los IDs existentes en Markdown y los prefijos `draft_`/`idea_`/`seed_`/`src_` para legibilidad)
- Índices apropiados para búsquedas frecuentes (status, platform, scheduled_at, created_at, enabled en sources)
- Engine: `create_engine(f"sqlite:///{db_path}")` con `connect_args={"check_same_thread": False}` para uso desde FastAPI

#### 11.3 Definir interfaces de repositorio

Crear `backend/src/social_agent/storage/repositories/` con:

- `base.py` — `Repository[T]` como `Protocol` con métodos CRUD genéricos (`save`, `get`, `list`, `delete`, `count`) — misma superficie que `MarkdownStore` actual
- `source_repository.py` — `SourceRepository` con métodos específicos (`list_active`, `find_by_type`)
- `seed_repository.py` — `SeedRepository` con métodos específicos (`list_by_status`, `list_by_source`)
- `idea_repository.py` — `IdeaRepository` con métodos específicos (`list_by_status`) — **añadido (gap del ROADMAP original)**
- `draft_repository.py` — `DraftRepository` con métodos específicos (`list_scheduled`, `list_by_platform`, `list_by_status`)

Se usa `Protocol` (structural typing) en vez de `ABC` para que `MarkdownStore` cumpla la interfaz por duck typing sin herencia explícita.

#### 11.4 Implementar repositorio SQLite con SQLAlchemy

- `sqlalchemy_repository.py` — Implementación concreta de cada repositorio usando SQLAlchemy 2.0 **sync** sessions
- Manejo de sesiones con `sessionmaker` (sesión por operación o por request)
- Mapeo de modelos ORM a modelos Pydantic del dominio (métodos `_to_pydantic`/`_to_orm` privados)
- Manejo de `media_urls`/`media_paths`/`tags`/`config` como columnas `JSON` en SQLite

#### 11.5 Mantener `MarkdownStore` como implementación alternativa

- `MarkdownStore` se mantiene como backend alternativo seleccionable vía `config.py` (no se deprecata)
- Ya cumple los `Protocol` definidos en 11.3 por duck typing (misma API `save`/`get`/`list`/`delete`/`count`/`list_scheduled`); se añaden stubs solo si falta algún método
- `config.py`: nuevo campo `storage_backend: str = "markdown"` (default seguro para no romper los 225 tests existentes)
- `storage/factory.py` con `get_*_repository(backend=settings.storage_backend)` para construir el repositorio adecuado

#### 11.6 Configurar Alembic

- `alembic init alembic` en `backend/`
- Configurar `alembic.ini` con `sqlalchemy.url`
- Crear migración inicial con todas las tablas
- Script de `seed` para datos iniciales (si aplica)

#### 11.7 Actualizar dependencias

- Añadir `sqlalchemy>=2.0`, `alembic>=1.13` a `pyproject.toml` (no `aiosqlite`: se usa SQLAlchemy sync)
- Opcional: `alembic-utils` para migraciones más complejas

#### 11.8 Migrar la lógica de negocio

- Crear `DatabaseStore` (o repositorios SQLite) que implementen los `Protocol` de 11.3
- Los agentes (`ideator.py`, `writer.py`) y publishers deben recibir el repositorio por inyección de dependencias
- Actualizar routers de FastAPI para usar los nuevos repositorios (vía `Depends` o factory)
- Actualizar comandos CLI para usar los nuevos repositorios vía factory
- **Adaptar `scheduler.py`:** cambiar el type hint de `run_once`/`run_loop` de `MarkdownStore[Draft]` a `DraftRepository` (Protocol) — los callers (CLI `schedule publish/worker` y `router_scheduler.py`) construyen el repositorio vía factory

#### 11.9 Estrategia de migración de datos

- Script `migrate_to_sqlite.py` que lea todos los archivos Markdown existentes y los inserte en SQLite
- Preservar IDs si es posible, o mantener un mapeo
- Ejecutar como comando CLI `social-agent db migrate`

#### 11.10 Tests

- Tests unitarios para cada repositorio (usando SQLite en memoria)
- Tests de integración con la base de datos real
- Tests de la migración de datos
- Verificar que todos los tests existentes siguen pasando (los de `MarkdownStore` deben coexistir)

### Fase 11 — Migración a base de datos (SQLite + patrón repositorio)

- [x] 11.1 — Dependencias: `sqlalchemy>=2.0`, `alembic>=1.13` añadidas; `settings.storage_backend` + `settings.sqlite_path` en `config.py`
- [x] 11.2 — `storage/db.py` con modelos ORM SQLAlchemy 2.0 sync: `sources`, `seeds`, `ideas` (gap del ROADMAP), `drafts`, `published` + FKs en cascada + índices (status, platform, scheduled_at, enabled)
- [x] 11.3 — `storage/repositories/` con `Protocol` interfaces: `Repository[T]` base + `SourceRepository`, `SeedRepository`, `IdeaRepository`, `DraftRepository` (structural typing, `MarkdownStore` cumple por duck typing)
- [x] 11.4 — `storage/sqlalchemy_repositories.py` con `SqlAlchemy{Source,Seed,Idea,Draft}Repository` (sesiones sync, mapeo ORM↔Pydantic, `_ensure_utc` para normalizar tzinfo, JSON columns para listas/dicts)
- [x] 11.4 — `storage/factory.py` con `get_*_repository(backend)` que selecciona `markdown` (default) o `sqlite` y crea tablas on first use
- [x] 11.5 — `storage/markdown_repositories.py` con wrappers `Markdown{Source,Seed,Idea,Draft}Repository` que heredan de `MarkdownStore` y añaden los métodos específicos; `MarkdownStore` sin cambios
- [x] 11.6 — Alembic configurado en `backend/alembic/`: `env.py` con `Base.metadata` + URL resuelta desde `settings`; migración inicial autogenerada (`1144f4016923_initial_schema.py`); `render_as_batch=True` para ALTER TABLE en SQLite; verificado upgrade/downgrade + no-drift
- [x] 11.7 — Dependencias (cubiertas en 11.1)
- [x] 11.8 — Routers FastAPI, CLI y `scheduler.py` migrados a usar `factory.get_*_repository()`: `run_once`/`run_loop` ahora reciben `DraftRepository` (Protocol); tests existentes siguen pasando sin cambios (backend markdown por defecto)
- [x] 11.9 — `storage/migrate_to_sqlite.py` con `migrate(data_dir, sqlite_path)` que lee Markdown y upserta en SQLite preservando IDs y FKs; comando CLI `social-agent db migrate` con flags `--data-dir` y `--sqlite-path`; idempotente
- [x] 11.10 — Tests: 308 tests totales, todos pasan (50 repos SQLite + 4 Alembic + 8 migración + 17 integración SQLite via API + 229 existentes); coexistencia Markdown/SQLite validada

---

### Notas técnicas

| Plataforma | API de media upload | Límite de imágenes | Formato |
|---|---|---|---|
| Twitter | `POST media/upload` (v1.1) + `media_ids` en create_tweet (v2) | 4 imágenes | PNG, JPEG, GIF, WEBP ≤ 5 MB |
| LinkedIn | `POST /rest/images` → `PUT` upload URL → incluir URN en post | 1 imagen por post | JPEG, PNG, GIF ≤ 10 MB |

---

## Fase 12 — Campo `comment` en ideas

### Contexto

El pipeline `seed → idea → draft` genera ideas cuyo `summary` es un resumen
**fiel** del artículo original, producido por el ideator. El usuario necesitaba
una vía para inyectar contexto personal o instrucciones de enfoque al agente
escritor (p. ej. "empieza narrando la publicación del modelo e indicando que es
de pesos abiertos" o "estaré probando este modelo esta semana"), manteniendo la
distinción clara entre los hechos de la noticia y la voz del autor.

### Plan de implementación

#### 12.1 Extender el modelo `Idea`

- Añadir campo opcional `comment: str | None = None` a `Idea`
- Incluirlo en `to_frontmatter()` / `from_frontmatter()` (compatible con ideas
  antiguas sin el campo)

#### 12.2 ORM SQLAlchemy + migración

- Añadir columna `comment` (Text, nullable) a `IdeaORM` en `storage/db.py`
- Mapear el campo en `SqlAlchemyIdeaRepository._to_orm` / `_to_pydantic`
- Migración Alembic `e616a71aa7d2_add_idea_comment.py` (add/drop column)

#### 12.3 Writer Agent: separar `summary` y `comment`

- `SYSTEM_PROMPT` ampliado con regla que distingue "Resumen de la noticia"
  (hechos verificables) de "Comentario del autor" (voz/instrucciones del
  usuario)
- `user_prompt` reestructurado en secciones; el bloque "Comentario del autor"
  solo se incluye si `idea.comment` no está vacío (sin ruido cuando no hay
  comentario → backward compatible)

#### 12.4 API REST

- `UpdateIdeaRequest` ampliado con `comment: str | None`
- `PATCH /api/ideas/{id}` gestiona `comment` (permite vaciar con `""`, no
  sobrescribe si el campo no viene en el body)

#### 12.5 CLI

- `ideas show` muestra `Comment:` si la idea tiene comentario
- Nuevo comando `ideas comment <id> <texto>` con flag `--clear`

#### 12.6 Frontend (Astro)

- Página de edición de ideas: textarea para el comentario + ayuda contextual
- Lista de ideas: icono indicador cuando la idea tiene comentario

#### 12.7 Tests

- `test_models.py`: roundtrip del campo `comment`, default `None`, carga de
  ideas legacy sin la clave
- `test_writer.py`: inclusión/omisión de la sección "Comentario del autor",
  distinción posicional summary vs comment
- `test_api.py`: set/clear/ignorar-missing del comentario
- `test_repositories_sqlalchemy.py`: roundtrip SQLite + update + clear
- `test_sqlite_integration.py`: update de comment vía API con backend SQLite
- `test_cli.py`: `ideas comment` set/clear/error/not-found + `ideas show`
  con/sin comentario

### Fase 12 — Campo `comment` en ideas

- [x] 12.1 — Modelo `Idea` con `comment: str | None` + frontmatter
- [x] 12.2 — `IdeaORM.comment` + mapeo en `SqlAlchemyIdeaRepository` + migración Alembic `e616a71aa7d2`
- [x] 12.3 — `WriterAgent`: `SYSTEM_PROMPT` + `user_prompt` separan "Resumen de la noticia" y "Comentario del autor" (solo si existe)
- [x] 12.4 — `PATCH /api/ideas/{id}` acepta `comment`; `GET` lo expone
- [x] 12.5 — CLI `ideas show` muestra el comentario; nuevo `ideas comment <id> <texto>` con `--clear`
- [x] 12.6 — Frontend: textarea en edición + icono indicador en lista
- [x] 12.7 — Tests: 330 tests totales, todos pasan (22 nuevos)

---

## Fase 13 — Alta manual de seeds desde URL

### Contexto

El pipeline `seed → idea → draft` solo permitía crear seeds desde fuentes
configuradas (`POST /api/seeds/generate`), que recolecta en lote desde RSS,
scrapers o social collectors. No existía vía para añadir un artículo individual
a partir de su URL, aunque `SourceType.manual` estaba definido en el modelo
`Source` pero sin usar, y `LinkScraperCollector` ya tenía la lógica de scrapeo
individual.

### Plan de implementación

#### 13.1 Refactorizar `link_scraper.py`

- Extraer `scrape_url(url, renderer) -> (title, content_markdown)` como función
  de módulo reutilizable, sin requerir una `Source`
- Extraer helpers `_fetch_page`, `_extract_title`, `_extract_content_html`
- `LinkScraperCollector._fetch_page` delega al helper de módulo para el caso
  httpx; mantiene browser persistente para playwright
- Exportar `scrape_url` desde `collectors/__init__.py`

#### 13.2 API REST

- `POST /api/seeds/scrape` — previsualiza el contenido de una URL sin guardar
  (body: `{url, renderer?}`)
- `POST /api/seeds` — alta manual de seed:
  - Body: `{url (req), title?, content?, tags?, scrape?, renderer?}`
  - Si `scrape=true` (default) y falta title/content, llama a `scrape_url`
  - `source_name = f"{domain} (manual)"`, `source_id = None`, `status = pending`
  - Sin dedup: permite crear varios seeds con la misma URL
  - Devuelve 201 + el seed

#### 13.3 CLI

- `social-agent seeds add <url>` con flags `--title`, `--content`, `--tags`,
  `--no-scrape`, `--renderer`

#### 13.4 Frontend (Astro)

- Botón "Add article" en `seeds.astro`
- Modal con: input URL + botón "Fetch" (scrapea y rellena), inputs editables
  de título, contenido y tags, botón "Save"
- Empty state actualizado

#### 13.5 Tests

- `test_api.py`: `TestScrapeSeedAPI` (4 tests) + `TestCreateSeedAPI` (7 tests)
- `test_cli.py`: `TestSeedsAdd` (7 tests)

### Fase 13 — Alta manual de seeds desde URL

- [x] 13.1 — `scrape_url()` refactorizado en `link_scraper.py` + exportado
- [x] 13.2 — `POST /api/seeds/scrape` (preview) + `POST /api/seeds` (alta manual)
- [x] 13.3 — CLI `seeds add <url>` con `--no-scrape`, `--title`, `--content`, `--tags`, `--renderer`
- [x] 13.4 — Frontend: botón "Add article" + modal con fetch + campos editables
- [x] 13.5 — Tests: 348 tests totales, todos pasan (18 nuevos)

---

## Fase 14 — Ordenación por recencia y filtros en todas las pantallas

### Contexto

Las cuatro pantallas de listado (sources, seeds, ideas, drafts) presentaban
inconsistencias: `sources` y `drafts` no ordenaban por `created_at` (el
`MarkdownStore.list()` devuelve los archivos ordenados por nombre, que no
coincide con el orden cronológico), y solo `seeds` disponía de barra de filtros
en la UI. Las demás pantallas solo aceptaban `?status=` vía URL, sin interfaz
de filtrado interactivo.

### Plan de implementación

#### 14.1 Ordenación por `created_at` descendente (backend)

- `router_sources.py`: `items.sort(key=lambda s: s.created_at or "", reverse=True)`
  tras `source_store.list()`
- `router_drafts.py`: `items.sort(key=lambda d: d.created_at or "", reverse=True)`
  tras `draft_store.list()`
- `router_ideas.py` y `router_seeds.py`: ya ordenaban — sin cambios
- Patrón aplicado a nivel de router (funciona con backends markdown y SQLite,
  ambos exponen `list(filter_fn=None)` con la misma firma)

#### 14.2 Filtros de búsqueda (backend)

- `GET /sources`: `source_types` (multi, además del `source_type` single
  existente), `q` (busca en name + url + tags), `enabled` (bool)
- `GET /ideas`: `statuses` (multi, además de `status` single), `q` (busca en
  title + summary)
- `GET /drafts`: `statuses` (multi) y `platforms` (multi, además de `platform`/
  `status` single existentes), `q` (busca en content)
- Todos los filtros son case-insensitive y combinables

#### 14.3 Barra de filtros en la UI (frontend)

- Replicar el sistema de chips "+ Add filter" de `seeds.astro` en `sources`,
  `ideas` y `drafts`:
  - **sources**: Type (checkboxes rss/webpage/link_scraper/social/manual),
    Keyword, Enabled (select All/Enabled/Disabled)
  - **ideas**: Status (checkboxes pending/used/discarded), Keyword
  - **drafts**: Status (checkboxes draft/approved/rejected/published/failed),
    Platform (checkboxes twitter/linkedin), Keyword
- Inputs de texto con debounce de 300ms
- Preservar deep-links del dashboard: `?status=` en ideas/drafts siembra el
  estado de filtros al cargar (compatibilidad con `index.astro`)

#### 14.4 Fecha de creación visible en sources

- `sources.astro` no mostraba `created_at`; se añade para que el orden
  "reciente arriba" sea verificable visualmente (igual que seeds/ideas/drafts)
- Badge "disabled" cuando `enabled === false`

#### 14.5 Tests

- `TestSourcesAPI`: orden + 5 filtros (source_type, source_types, q en name,
  q en tags, enabled)
- `TestIdeasAPI`: orden + 4 filtros (status, statuses, q en title, q en summary)
- `TestDraftsAPI`: orden + 5 filtros (status, statuses, platform, platforms, q)
- Tests de ordenación usan IDs con orden alfabético inverso al cronológico
  (p. ej. `src_a`=2020, `src_z`=2025) para verificar que el sort revierte el
  orden de archivos

### Fase 14 — Ordenación por recencia y filtros en todas las pantallas

- [x] 14.1 — `router_sources` y `router_drafts` ordenan por `created_at` desc
- [x] 14.2 — Filtros `q`/`statuses`/`source_types`/`platforms`/`enabled` en backend
- [x] 14.3 — Barra de filtros en sources, ideas y drafts (chips "+ Add filter")
- [x] 14.4 — `created_at` visible en `sources.astro` + badge "disabled"
- [x] 14.5 — Tests: 365 tests totales, todos pasan (17 nuevos); build frontend OK

---

## Fase 15 — Suite de tests básica del frontend

### Contexto

El frontend (Astro + TypeScript) carecía por completo de tests automatizados.
Toda la lógica testeable vive en `src/scripts/*.ts` (módulos importados por los
`<script>` inline de las páginas): `icons.ts`, `card.ts`, `dom.ts`, `types.ts`.
Las páginas `.astro` contienen lógica inline que habla con la API en
`localhost:8000`, fuera del alcance de una suite "básica".

### Plan de implementación

#### 15.1 Stack y configuración

- **Vitest** ^2.1 como runner (rápido, hereda el alias `~/*` del tsconfig).
- **happy-dom** ^15 como entorno DOM ligero (sin descargar navegadores).
- **@types/node** ^22 para tipar `node:url` en `vitest.config.ts`.
- `frontend/vitest.config.ts` con alias `~ → ./src`, entorno `happy-dom`,
  `include: src/**/*.test.ts`, coverage v8 sobre `src/scripts/**/*.ts`.
- `tsconfig.json`: `types: ["astro/client", "node"]` para que `astro check`
  no falle al type-checkar `vitest.config.ts`.
- Scripts en `package.json`: `test`, `test:watch`, `test:coverage`.

#### 15.2 Tests unitarios sobre `src/scripts/`

- `icons.test.ts` (12 tests): `iconPath` existente/inexistente, `icon` con
  size por defecto/personalizado/clase, `ICON_NAMES` sin duplicados.
- `dom.test.ts` (19 tests): `byId`, `q`, `qAll` contra DOM real (happy-dom);
  `getErrorMessage` con detail string/array/no-JSON; `esc` y `escAttr`
  escapan `<`, `>`, `&`, `"` y neutralizan payloads XSS.
- `card.test.ts` (34 tests): `entityCard` con/sin body, `cardTitle` con XSS
  de atributo (verificado via parseo DOM), `contextBadge`, `statusBadgeSoft`,
  `actionBtn`/`actionEdit`/`actionDisabled`/`copyBtn` con escaping de
  atributos, `metaChip`, `tagChips` con XSS, `urlRow` hostname vs fallback,
  `actionsWrap`/`metaWrap`.

#### 15.3 Verificación

- `pnpm test` — 65 tests pasan.
- `pnpm check` — 0 errores (astro check).
- `pnpm build` — build exitoso (9 páginas).

### Fase 15 — Suite de tests básica del frontend

- [x] 15.1 — Vitest + happy-dom + @types/node; `vitest.config.ts` + scripts `test`/`test:watch`/`test:coverage`; `tsconfig.json` con `types: ["astro/client", "node"]`
- [x] 15.2 — 65 tests: 12 icons + 19 dom + 34 card (incluye casos XSS de texto y atributo via parseo DOM)
- [x] 15.3 — `pnpm test` (65 pass), `pnpm check` (0 errores), `pnpm build` OK

---

## Fase 16 — Migración del frontend a pnpm

### Contexto

El frontend usaba npm como gestor de paquetes. Se migra a pnpm para alinear
con prácticas modernas del ecosistema Node (mejor rendimiento, disco
compartido vía store global, lockfile determinista, resolución estricta de
dependencias que evita imports fantasma).

### Plan de implementación

#### 16.1 Configuración

- `frontend/package.json`: campo `packageManager: "pnpm@10.30.3"` (corepack)
- `frontend/package.json`: sección `pnpm.onlyBuiltDependencies` aprobando
  `esbuild` y `sharp` (pnpm 10 bloquea por defecto los postinstall scripts;
  ambos son necesarios para Vite/Vitest y Astro respectivamente)
- Eliminado `frontend/package-lock.json`
- Generado `frontend/pnpm-lock.yaml`

#### 16.2 Documentación

- `README.md`: pnpm añadido a "Requisitos"; `pnpm install` en "Instalación";
  `pnpm dev` y `pnpm test` en "Servidores" y "Desarrollo"
- `ROADMAP.md`: referencias `npm run` → `pnpm` en la Fase 15

#### 16.3 Verificación

- `pnpm install` — 398 paquetes, build scripts de esbuild+sharp ejecutados
- `pnpm test` — 65 tests pasan
- `pnpm check` — 0 errores (astro check)
- `pnpm build` — 9 páginas construidas OK

### Fase 16 — Migración del frontend a pnpm

- [x] 16.1 — `packageManager: pnpm@10.30.3` + `pnpm.onlyBuiltDependencies` (esbuild, sharp); `package-lock.json` eliminado; `pnpm-lock.yaml` generado
- [x] 16.2 — README.md actualizado (Requisitos, Instalación, Servidores, Desarrollo); ROADMAP.md actualizado
- [x] 16.3 — `pnpm install` + `pnpm test` (65 pass) + `pnpm check` (0 errores) + `pnpm build` OK

---

## Fase 17 — Interpretación correcta de zona horaria en `schedule`

### Contexto

Al lanzar `schedule list` se veían publicaciones "vencidas" que no se
publicaban. Causa raíz: los datetimes naive (sin offset) que el usuario
introducía por CLI pensando en hora local se persistían como naive y, al
compararlos contra `datetime.now(timezone.utc)`, se interpretaban como UTC
— desplazando la hora real 1–2 horas hacia el futuro según DST. Así un
draft programado para las 15:30 local se publicaba a las 15:30 UTC = 17:30
local (en Madrid en verano), dando la sensación de "vencido sin publicar".

### Plan de implementación

#### 17.1 Zona horaria configurable

- Nuevo campo `settings.timezone: str = "Europe/Madrid"` (override vía
  `SOCIAL_AGENT_TIMEZONE`), nombre IANA.
- `config.py`: helper `get_tz(name=None) -> ZoneInfo` con cache por nombre
  (`lru_cache` sobre `_zoneinfo`); lee `settings.timezone` en cada llamada
  para que monkeypatch en tests sea efectivo.

#### 17.2 Helpers de conversión

- Nuevo módulo `backend/src/social_agent/timezone_utils.py`:
  - `localize_to_utc(dt)`: naive → TZ configurada → UTC-aware; aware →
    normalizado a UTC (respeta offset original).
  - `to_local_iso(dt)`: aware → TZ configurada → string ISO para display
    (naive se asume UTC por la invariante de dominio).

#### 17.3 CLI

- `_parse_scheduled_at` aplica `localize_to_utc` al resultado de
  `datetime.fromisoformat` → los drafts se guardan siempre UTC-aware
  (refuerza la invariante de dominio).
- `schedule set`: el echo muestra hora local y UTC, p. ej.
  `scheduled for 2026-06-22T16:30:00+02:00 (14:30:00+00:00)`.
- `schedule list`: muestra `to_local_iso(d.scheduled_at)` en vez del ISO
  crudo UTC.

#### 17.4 MarkdownStore

- `list_scheduled` cambia la rama naive de `replace(tzinfo=utc)` a
  `replace(tzinfo=get_tz()).astimezone(utc)`: los drafts legacy con
  `scheduled_at` naive se re-interpretan como hora local al evaluar si
  están vencidos — migra automáticamente el estado pendiente.
- La rama aware se queda igual.
- `sqlalchemy_repositories.list_scheduled` **sin cambios**: ahí los naive
  llegan vía pysqlite (genuinamente UTC, ya normalizados por `_ensure_utc`
  en `_to_pydantic`).

#### 17.5 API REST

- `POST /api/drafts/{id}/schedule` aplica `localize_to_utc` al
  `scheduled_at` del body para coherencia CLI↔API.

#### 17.6 Tests

- `tests/test_cli.py`: fixture autouse `_default_utc_timezone` fija
  `settings.timezone = "UTC"` para no romper los tests existentes; nueva
  clase `TestScheduleTimezone` con 4 tests (naive→UTC+1, offset explícito
  respetado, echo con ambas representaciones, list muestra hora local y
  no filtra UTC).
- `tests/test_markdown_store.py`: 2 tests nuevos sobre
  `list_scheduled` con naive interpretado como TZ configurada (due y
  future boundary) usando `Africa/Lagos` (UTC+1 sin DST, determinista).
- `test_set_schedule` reforzado con `restored.scheduled_at.tzinfo is not None`.

### Fase 17 — Interpretación correcta de zona horaria en `schedule`

- [x] 17.1 — `settings.timezone` + `get_tz()` con cache en `config.py`
- [x] 17.2 — `timezone_utils.py` con `localize_to_utc` y `to_local_iso`
- [x] 17.3 — CLI `_parse_scheduled_at` / `schedule set` / `schedule list` actualizados
- [x] 17.4 — `MarkdownStore.list_scheduled` interpreta naive como TZ configurada
- [x] 17.5 — `POST /api/drafts/{id}/schedule` aplica `localize_to_utc`
- [x] 17.6 — Tests: 371 tests totales, todos pasan (+6 nuevos); ruff sin nuevos errores
- [x] Documentación: `docs/publicacion-programada.md` + `.env.example` actualizados

---

## Fase 18 — Eliminación permanente de borradores

### Contexto

No existía forma de eliminar un borrador: una vez generado, el fichero
markdown quedaba en `data/drafts/` indefinidamente, incluso tras ser
rechazado o abandonado. Además, al borrar "a mano" los borradores de una
idea, ésta se quedaba bloqueada en estado `used` (o `discarded`) sin forma
de volver a generar borradores sobre ella, obligando a intervenir el
frontmatter manualmente.

### Plan de implementación

#### 18.1 API REST

- Nuevo endpoint `DELETE /api/drafts/{draft_id}` (status 204) en
  `router_drafts.py`. Devuelve 404 si no existe y 400 si el borrador está
  `published` (no se permite borrar el registro de algo ya publicado en
  redes).
- Tras borrar, si la idea asociada (`draft.idea_id`) se queda sin ningún
  borrador, se revierte a `IdeaStatus.pending` con independencia del estado
  previo (`used`, `discarded`, ...) para poder reutilizarla. La escritura
  se omite si la idea ya estaba `pending` (no-op idempotente).

#### 18.2 CLI

- Nuevo comando `drafts delete <draft_id>` en `commands.py` con la misma
  lógica (bloqueo de `published` + reversión de idea). Mensaje extra
  `Idea '<id>' reverted to pending.` cuando procede.

#### 18.3 Frontend

- `drafts.astro`: botón "Eliminar" (icono `trash`) en cada tarjeta, oculto
  para borradores `published`. Confirmación vía modal `confirm-dialog`
  existente; llama a `DELETE /api/drafts/{id}` y recarga la lista.
- `drafts/edit.astro`: botón "Eliminar" (estilo `btn-error btn-outline`)
  en el pie del formulario, oculto para `published`. Confirmación vía
  `window.confirm`; redirige a `/drafts` tras borrar.

#### 18.4 Tests

- `tests/test_api.py` — `TestDraftsDeleteAPI` (6 tests): borrado OK,
  not found, published bloqueado, último borrador revierte idea, idea se
  mantiene cuando quedan borradores, reversión independiente del estado.
- `tests/test_cli.py` — `TestDraftsDelete` (6 tests): equivalente CLI +
  caso idea ya `pending` (sin mensaje de reversión).

### Fase 18 — Eliminación permanente de borradores

- [x] 18.1 — `DELETE /api/drafts/{draft_id}` con bloqueo de `published` y reversión de idea
- [x] 18.2 — Comando CLI `drafts delete` con misma lógica
- [x] 18.3 — Frontend: botón eliminar en listado y edición de borradores
- [x] 18.4 — Tests: +12 tests backend; `pnpm check` 0 errores; `pnpm test` 69 pass; `pnpm build` OK
