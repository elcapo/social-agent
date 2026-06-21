# Semillas (`seeds`)

Las **semillas** son el segundo paso del flujo de trabajo
(fuentes → semillas → ideas → borradores).

Son ideas generales para posts, generadas por el *agente ideador* a partir de las
fuentes y tus intereses. Se generan, listan, revisan y pueden descartarse.

## Comandos

```bash
# Generar semillas desde las fuentes configuradas y el prompt de intereses
social-agent seeds generate

# Generar usando un fichero de intereses alternativo
social-agent seeds generate --interests data/prompts/mis-intereses.md

# Ver la respuesta cruda del LLM sin guardar (útil para depuración)
social-agent seeds generate --dry-run

# Añadir un artículo individual a partir de su URL (scrapea título y contenido)
social-agent seeds add "https://ejemplo.com/articulo"

# Añadir con título y contenido manuales (sin scrapeo)
social-agent seeds add "https://ejemplo.com/articulo" --no-scrape --title "Título" --content "Contenido"

# Añadir con tags
social-agent seeds add "https://ejemplo.com/articulo" --tags "tech, ai"

# Ver todas las semillas
social-agent seeds list

# Ver solo las pendientes
social-agent seeds list --status pending

# Ver el detalle de una semilla
social-agent seeds show <seed_id>

# Descartar una semilla
social-agent seeds discard <seed_id>
```

## Estados

Las semillas pueden tener estos estados:

| Estado     | Significado                                     |
|------------|-------------------------------------------------|
| `pending`  | Recién generada, pendiente de revisión          |
| `used`     | Ya se ha usado para generar una idea o borrador |
| `discarded`| Descartada manualmente                          |
