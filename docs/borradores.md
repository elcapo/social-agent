# Borradores (`drafts`)

Los **borradores** son el último paso del flujo de trabajo
(fuentes → semillas → ideas → borradores).

Son versiones concretas del post adaptadas a cada plataforma (Twitter, LinkedIn,
etc.), generadas por el *agente escritor* a partir de una idea. Se revisan,
editan, aprueban y publican.

## Comandos

```bash
# Ver todos los borradores
social-agent drafts list

# Ver los borradores de Twitter
social-agent drafts list --platform twitter

# Ver los borradores aprobados
social-agent drafts list --status approved

# Ver el detalle de un borrador
social-agent drafts show <draft_id>

# Aprobar un borrador para su publicación
social-agent drafts approve <draft_id>

# Rechazar un borrador con una nota
social-agent drafts reject <draft_id> --notes "muy técnico"

# Editar un borrador
social-agent drafts edit <draft_id> "nuevo contenido"

# Publicar en la red social real (requiere credenciales configuradas)
social-agent drafts publish <draft_id>
```

## Estados

Los borradores pueden tener estos estados:

| Estado     | Significado                                              |
|------------|----------------------------------------------------------|
| `draft`    | Recién generado, pendiente de revisión                   |
| `approved` | Aprobado para publicación                                |
| `rejected` | Rechazado manualmente                                    |
| `published`| Publicado con éxito en la red social                     |
| `failed`   | Falló la publicación (revisa `publish_error` con `show`) |

Solo los borradores en estado `approved` pueden publicarse.

Para inspeccionar el error en borradores fallidos:

```bash
social-agent drafts show <draft_id>
```
