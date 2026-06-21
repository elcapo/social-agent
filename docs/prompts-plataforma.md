# Prompts de plataforma

Los prompts viven en `data/prompts/`. Hay dos tipos:

- `interests.md` — intereses del usuario (usado por el IdeatorAgent)
- `platforms/*.md` — instrucciones de tono/estilo por plataforma (usado por el WriterAgent)

## interests.md

Archivo en `data/prompts/interests.md` con frontmatter YAML y cuerpo markdown:

```markdown
---
title: Soberanía, ética y pedagogía digital
priority: 1
---

1. soberanía digital (software libre, modelos de pesos abiertos, etc)
2. ética digital (tecnologías aplicadas a causas sociales, privacidad, etc)
3. pedagogía digital (lecciones de programación y otros fundamentos)
```

Solo el cuerpo del markdown se pasa al prompt. El frontmatter (`title`,
`priority`) se ignora en la generación. Ver [agente-ideador.md](agente-ideador.md).

## platforms/*.md

Cada plataforma tiene un archivo markdown en `data/prompts/platforms/` con
frontmatter YAML y cuerpo markdown:

```markdown
---
title: Twitter / X
lang: es
max_chars: 280
---

Tono: Directo, técnico pero accesible, con gancho...
```

| Archivo           | Plataforma |
|-------------------|------------|
| `twitter.md`      | Twitter/X  |
| `linkedin.md`     | LinkedIn   |

### Frontmatter

| Campo       | Descripción                              |
|-------------|------------------------------------------|
| `title`     | Nombre legible de la plataforma          |
| `lang`      | Idioma del contenido                     |
| `max_chars` | Límite de caracteres (0 = sin límite)    |

### Cuerpo

Contiene instrucciones de tono, estilo, ejemplos aceptables y no aceptables.
Solo el cuerpo se pasa al LLM. Ver [agente-escritor.md](agente-escritor.md).

## Personalización

Para editar estos prompts, copia los ejemplos de `templates/` a `data/` y
 modifícalos. Ver [personalizacion-prompts.md](personalizacion-prompts.md).
