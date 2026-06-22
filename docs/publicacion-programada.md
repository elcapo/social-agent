# Publicación programada (`schedule`)

Los borradores pueden programarse para publicarse automáticamente en una fecha
futura. El scheduler comprueba periódicamente qué drafts han llegado a su hora y
los publica con las credenciales configuradas.

## Comandos

```bash
# Programar un borrador (formato ISO 8601, con o sin zona horaria)
social-agent schedule set <draft_id> 2026-06-20T15:30:00
```

Las fechas **sin zona horaria** (naive) se interpretan en la zona horaria
configurada (`SOCIAL_AGENT_TIMEZONE`, por defecto `Europe/Madrid`) y se
almacenan internamente como UTC. Las fechas **con offset explícito**
(p. ej. `2026-06-20T15:30:00+02:00` o `...Z`) se respetan y se normalizan a
UTC. El comando confirma mostrando ambas representaciones:

```
Draft 'draft_xxx' scheduled for 2026-06-20T17:30:00+02:00 (2026-06-20T15:30:00+00:00).
```

```bash
# Listar borradores programados (ordenados por fecha, en hora local)
social-agent schedule list

# Cancelar la programación de un borrador
social-agent schedule cancel <draft_id>

# Publicar ahora todos los drafts cuya hora ha llegado (one-shot)
social-agent schedule publish
```

> [!NOTE]
> `schedule list` solo *lista*; no publica. Para que los drafts vencidos se
> publiquen debes ejecutar `schedule publish` manualmente o mantener el
> `schedule worker` corriendo (ver más abajo).

## Lanzar el "cron" (worker en segundo plano)

Para que la publicación programada funcione de forma automática, ejecuta el
worker del scheduler en un proceso aparte (en una terminal, un `tmux`/`screen`,
o como servicio systemd):

```bash
# Comprueba cada 5 minutos (por defecto) y publica los drafts vencidos
uv run social-agent schedule worker

# Intervalo personalizado (en segundos)
uv run social-agent schedule worker --interval 60
```

El worker se ejecuta en primer plano hasta que lo detienes con `Ctrl+C`.
Mientras esté activo, cualquier draft con `scheduled_at` en el pasado y estado
`draft` se publicará automáticamente en su plataforma.
