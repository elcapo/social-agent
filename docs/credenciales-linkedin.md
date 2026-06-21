# Credenciales de LinkedIn

Los colectores y publicadores de LinkedIn requieren credenciales OAuth 2.0.

## Obtener las credenciales

1. Ve a [developer.linkedin.com](https://developer.linkedin.com) y crea una app.
2. Configura el redirect URI como `http://localhost:8080/callback`.
3. Añade el Client ID y Client Secret al `.env`:

```env
SOCIAL_AGENT_LINKEDIN_CLIENT_ID=xxxxxxxxx
SOCIAL_AGENT_LINKEDIN_CLIENT_SECRET=xxxxxxxxx
```

4. Genera el token de acceso automáticamente:

```bash
social-agent linkedin auth --save
```

Esto abrirá el navegador para autorizar la app y guardará el token en `.env`.
Scopes solicitados: `openid`, `profile`, `w_member_social`.

Opcionalmente puedes predefinir el author URN (se resuelve automáticamente si se omite):

```env
SOCIAL_AGENT_LINKEDIN_AUTHOR_URN=urn:li:person:xxx
```

Sin estas credenciales el colector social de LinkedIn devuelve lista vacía y el
publicador informa del error.
