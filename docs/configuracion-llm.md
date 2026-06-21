# Configuración del proveedor LLM

El sistema usa [LiteLLM](https://litellm.vercel.app/) y soporta cualquier
proveedor compatible (OpenAI, Anthropic, Ollama, etc.).

El acceso a los modelos se hace a través de **OpenCode**, que expone endpoints
compatibles con la API de OpenAI. Hay dos modalidades:

## OpenCode Go (suscripción)

Endpoint con modelos de alto rendimiento incluidos en la suscripción.

```env
SOCIAL_AGENT_LLM_PROVIDER=openai/glm-5.2
SOCIAL_AGENT_LLM_API_KEY=sk-...   # Tu API key de https://opencode.ai/auth
SOCIAL_AGENT_LLM_BASE_URL=https://opencode.ai/zen/go/v1
```

Otros modelos disponibles vía Go:

```env
# SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-flash
# SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-pro
# SOCIAL_AGENT_LLM_PROVIDER=openai/kimi-k2.7
```

## OpenCode Zen (pago por uso)

API de pago por uso, incluye un capa gratuita sin coste.

```env
# OpenCode Zen (DeepSeek V4 Flash Free — sin coste)
SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-flash-free
SOCIAL_AGENT_LLM_API_KEY=sk-...   # Tu API key de https://opencode.ai/auth
SOCIAL_AGENT_LLM_BASE_URL=https://opencode.ai/zen/v1
```

Otros modelos disponibles vía Zen (`https://opencode.ai/docs/zen/`):

```env
# SOCIAL_AGENT_LLM_PROVIDER=openai/deepseek-v4-flash
# SOCIAL_AGENT_LLM_PROVIDER=openai/gpt-5.4-nano
# SOCIAL_AGENT_LLM_PROVIDER=openai/claude-sonnet-4-6
```

## Otros proveedores

También puedes usar cualquier otro proveedor directamente:

```env
# OpenAI directo
# SOCIAL_AGENT_LLM_PROVIDER=openai/gpt-4o
# SOCIAL_AGENT_LLM_API_KEY=sk-...

# Anthropic Claude
# SOCIAL_AGENT_LLM_PROVIDER=claude-3-haiku-20240307
# SOCIAL_AGENT_LLM_API_KEY=sk-ant-...

# Ollama (local)
# SOCIAL_AGENT_LLM_PROVIDER=ollama/llama3
# SOCIAL_AGENT_LLM_BASE_URL=http://localhost:11434
```
