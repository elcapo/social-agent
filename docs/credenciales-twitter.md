# Credenciales de Twitter / X

Los colectores y publicadores de Twitter requieren credenciales de la API v2.

## Obtener las credenciales

1. Ve a [developer.twitter.com](https://developer.twitter.com) y crea un proyecto.
2. Para el **colector** (lectura): genera un *Bearer Token* en "Keys and Tokens".
3. Para el **publicador** (escritura): genera credenciales OAuth 1.0a User Context
   con permisos de escritura en "Keys and Tokens" → "Access Token and Secret".
4. Añádelas al `.env`:

```env
# Colector (lectura)
SOCIAL_AGENT_TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAA...

# Publicador (escritura)
SOCIAL_AGENT_TWITTER_API_KEY=xxxxxxxxx
SOCIAL_AGENT_TWITTER_API_SECRET=xxxxxxxxx
SOCIAL_AGENT_TWITTER_ACCESS_TOKEN=xxxxxxxxx
SOCIAL_AGENT_TWITTER_ACCESS_TOKEN_SECRET=xxxxxxxxx
```

Sin estas credenciales el colector social de Twitter devuelve lista vacía y el
publicador informa del error.
