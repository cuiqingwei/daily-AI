import requests
import json

url = "http://popos:11434/api/chat"
payload = {
    "model": "qwen3.5:4b",
    "messages": [{"role": "user", "content": "你好，请用中文介绍你自己。"}],
    "stream": False
}

print(f"Testing native Ollama Chat API at {url}...")
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        message = res_json.get("message", {})
        content = message.get("content", "")
        print(f"Response (length: {len(content)}):")
        print(content)
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
