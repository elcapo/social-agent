# Fuentes (`sources`)

Las **fuentes** son el primer paso del flujo de trabajo
(fuentes → semillas → ideas → borradores).

Registra de dónde quieres obtener información (RSS, webs, APIs sociales). Cada
fuente tiene una **prioridad** (1 alta, 3 baja) que el *agente ideador* usará
para ponderar su contenido.

## Comandos

```bash
# Añadir una fuente RSS
social-agent sources add "Rust Blog" rss "https://blog.rust-lang.org/feed" --priority 1

# Listar todas las fuentes
social-agent sources list
```

## Tipos de fuente

| `source_type` | Descripción                                  |
|---------------|----------------------------------------------|
| `rss`         | Feed RSS/Atom                                |
| `webpage`     | Página web (scrapeo de contenido)            |
| `social`      | API social (Twitter/LinkedIn)                |
| `link_scraper`| Scrapeo puntual de una URL                   |
| `manual`      | Entrada manual (sin recolección automática)  |

## Prioridades

| Valor | Significado |
|-------|-------------|
| `1`   | Alta         |
| `2`   | Media        |
| `3`   | Baja         |
