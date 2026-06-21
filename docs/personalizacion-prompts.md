# Personalización de prompts

Los prompts que usan los agentes se cargan desde `data/prompts/`. Para
personalizarlos, copia los ejemplos de `templates/` y edítalos:

```bash
cp templates/prompts/interests.md data/prompts/
cp -r templates/prompts/platforms data/prompts/
```

Luego ajusta:

- `data/prompts/interests.md` con tus temas de interés
- `data/prompts/platforms/*.md` con el tono y ejemplos para cada red

Para el formato de estos archivos, ver
[prompts-plataforma.md](prompts-plataforma.md).
