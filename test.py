import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "gemma3:4b",
        "prompt": "Di hola en una frase",
        "stream": False
    }
)

data = response.json()
print(data.get("response") or data.get("message", {}).get("content"))