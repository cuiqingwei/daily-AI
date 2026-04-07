import requests
import json
import time

url = "http://popos:1234/v1/chat/completions"
payload = {
    "model": "google/gemma-4-e2b",
    "messages": [{"role": "user", "content": "你是一个专业的 GitHub 开源项目分析师。请写一份 100 字左右的中文趋势总结。"}],
    "stream": False
}

print(f"Testing native LLM API speed at {url}...")
try:
    # 计时开始
    start_time = time.time()
    response = requests.post(url, json=payload, timeout=120)
    elapsed = time.time() - start_time

    print(f"Status: {response.status_code}")
    print(f"Time: {elapsed:.2f}s")

    if response.status_code == 200:
        res_json = response.json()
        content = res_json.get("choices", [{}])[0].get("message", {}).get("content", "")
        tokens = res_json.get("usage", {}).get("completion_tokens", 0)
        print(f"Response (length: {len(content)}, tokens: {tokens})")
        if tokens > 0:
            print(f"Speed: {tokens/elapsed:.1f} tokens/s")
        print(content)
except Exception as e:
    print(f"Error: {e}")
