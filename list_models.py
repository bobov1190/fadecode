"""Печатает бесплатные модели OpenRouter: их id копируй в AI_MODELS в .env."""
import json
import urllib.request

with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as resp:
    models = json.loads(resp.read().decode("utf-8"))["data"]

free = sorted(m["id"] for m in models if m["id"].endswith(":free"))
print("Бесплатные модели (%d):" % len(free))
for m in free:
    print("  " + m)
print("\nПример: AI_MODELS=openrouter/free," + ",".join(free[:3]))
