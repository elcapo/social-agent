# API REST

La API está documentada automáticamente con OpenAPI:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/sources` | Listar fuentes (filtro opcional `?source_type=rss`) |
| `POST` | `/api/sources` | Crear fuente |
| `GET` | `/api/sources/{id}` | Obtener fuente |
| `PATCH` | `/api/sources/{id}` | Actualizar fuente |
| `DELETE` | `/api/sources/{id}` | Eliminar fuente |
| `GET` | `/api/seeds` | Listar semillas (filtros opcionales: `?status=pending`, `?statuses=pending&statuses=approved`, `?q=keyword`, `&url=fragment`) |
| `GET` | `/api/seeds/{id}` | Obtener semilla |
| `POST` | `/api/seeds` | Añadir artículo manualmente (body: `{"url": "...", "title?": "...", "content?": "...", "tags?": [...], "scrape?": true}`) |
| `POST` | `/api/seeds/scrape` | Previsualizar contenido de una URL sin guardar (body: `{"url": "..."}`) |
| `POST` | `/api/seeds/generate` | Generar semillas desde fuentes |
| `PATCH` | `/api/seeds/{id}` | Actualizar semilla |
| `GET` | `/api/ideas` | Listar ideas (`?status=pending`) |
| `GET` | `/api/ideas/{id}` | Obtener idea (incluye `comment`) |
| `POST` | `/api/ideas/generate` | Generar idea desde una semilla aprobada |
| `PATCH` | `/api/ideas/{id}` | Actualizar idea (estado, título, resumen, **comentario**) |
| `DELETE` | `/api/ideas/{id}` | Eliminar idea |
| `GET` | `/api/drafts` | Listar borradores (`?platform=twitter&status=approved`) |
| `GET` | `/api/drafts/scheduled` | Listar borradores programados |
| `GET` | `/api/drafts/{id}` | Obtener borrador |
| `POST` | `/api/drafts/generate` | Generar borradores desde una semilla |
| `PATCH` | `/api/drafts/{id}` | Actualizar borrador (estado, contenido, notas) |
| `POST` | `/api/drafts/{id}/schedule` | Programar borrador (body: `{"scheduled_at": "2026-06-20T15:30:00"}`) |
| `POST` | `/api/drafts/{id}/unschedule` | Eliminar la programación de un borrador |
| `POST` | `/api/scheduler/run` | Ejecutar el scheduler (publica drafts vencidos) |
| `POST` | `/api/publish/{id}` | Publicar borrador aprobado en la red social |

## Ejemplos con curl

```bash
# Health
curl http://localhost:8000/api/health

# Crear fuente RSS
curl -X POST "http://localhost:8000/api/sources?name=Rust+Blog&source_type=rss&url=https://blog.rust-lang.org/feed"

# Listar fuentes
curl http://localhost:8000/api/sources

# Añadir un artículo individual como semilla (scrapea título y contenido)
curl -X POST http://localhost:8000/api/seeds \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ejemplo.com/articulo"}'

# Previsualizar el contenido scrapeado sin guardarlo
curl -X POST http://localhost:8000/api/seeds/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://ejemplo.com/articulo"}'

# Generar semillas
curl -X POST http://localhost:8000/api/seeds/generate \
  -H "Content-Type: application/json" \
  -d '{"interests": "rust, systems programming"}'

# Generar una idea desde una semilla aprobada
curl -X POST http://localhost:8000/api/ideas/generate \
  -H "Content-Type: application/json" \
  -d '{"seed_id": "seed_123", "interests": "rust, systems programming"}'

# Añadir un comentario del autor a una idea (lo recibe el agente escritor)
curl -X PATCH http://localhost:8000/api/ideas/idea_123 \
  -H "Content-Type: application/json" \
  -d '{"comment": "estaré probando este modelo esta semana, publicaré actualizaciones"}'

# Generar drafts (requiere idea existente)
curl -X POST http://localhost:8000/api/drafts/generate \
  -H "Content-Type: application/json" \
  -d '{"idea_id": "idea_123", "platforms": ["twitter", "linkedin"]}'

# Aprobar draft
curl -X PATCH http://localhost:8000/api/drafts/draft_123 \
  -H "Content-Type: application/json" \
  -d '{"status": "approved"}'

# Publicar (requiere credenciales configuradas)
curl -X POST http://localhost:8000/api/publish/draft_123

# Programar un borrador para una fecha futura
curl -X POST http://localhost:8000/api/drafts/draft_123/schedule \
  -H "Content-Type: application/json" \
  -d '{"scheduled_at": "2026-06-20T15:30:00+00:00"}'

# Ejecutar el scheduler manualmente (publica drafts vencidos)
curl -X POST http://localhost:8000/api/scheduler/run
```
