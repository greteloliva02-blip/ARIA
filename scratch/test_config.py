from core.config import Config
cfg = Config()
print('Mistral API Key:', cfg.MISTRAL_API_KEY)
print('Mistral Model:', cfg.MISTRAL_MODEL)
print('Ollama Model:', cfg.OLLAMA_MODEL)
