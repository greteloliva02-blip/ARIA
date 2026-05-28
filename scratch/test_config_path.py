import sys, os
# Ensure project root is in sys.path
sys.path.append(os.path.abspath('C:/ARIA'))

from core.config import Config
cfg = Config()
print('MISTRAL_API_KEY:', cfg.MISTRAL_API_KEY)
print('MISTRAL_MODEL:', cfg.MISTRAL_MODEL)
print('OLLAMA_MODEL:', cfg.OLLAMA_MODEL)
print('OLLAMA_BASE_URL:', cfg.OLLAMA_BASE_URL)
