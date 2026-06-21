# Ideas (`ideas`)

Las **ideas** son el paso intermedio entre las semillas y los borradores
(fuentes → semillas → ideas → borradores).

El *agente ideador* produce, a partir de una semilla aprobada, un `title` y un
`summary` fiel al artículo original. Sobre esa idea puedes añadir un
**comentario** del autor que se enviará al *agente escritor* **separado del
resumen de la noticia**, para aportar contexto personal o instrucciones de
enfoque (p. ej. "empieza narrando la publicación del modelo e indicando que es
de pesos abiertos").

## Comandos

```bash
# Generar una idea a partir de una semilla aprobada
social-agent ideas generate <seed_id>

# Listar ideas
social-agent ideas list
social-agent ideas list --status pending

# Ver el detalle de una idea (incluye el comentario si lo tiene)
social-agent ideas show <idea_id>

# Fijar un comentario para el escritor
social-agent ideas comment <idea_id> "estaré probando este modelo esta semana"

# Eliminar el comentario
social-agent ideas comment <idea_id> --clear

# Descartar una idea
social-agent ideas discard <idea_id>
```

El comentario también puede editarse desde el frontend (página de edición de la
idea) o vía API con `PATCH /api/ideas/{id}` enviando `{"comment": "..."}`.
