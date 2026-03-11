import requests
import json

url = "http://mbp:11434/api/generate"
prompt = """你是一个专业的 GitHub 开源项目分析师。请写一份 100 字左右的中文趋势总结。"""
payload = {
    "model": "qwen3.5:4b",
    "prompt": prompt,
    "stream": False
}

print(f"Testing native Ollama API with prompt at {url}...")
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        content = res_json.get("response", "")
        print(f"Response (length: {len(content)}):")
        print(content)
except Exception as e:
    print(f"Error: {e}")
