import requests
import json

# for LM Studio Test
url = "http://popos:1234/v1/chat/completions"
payload = {
    "model": "google/gemma-4-e2b",
    "messages": [{"role": "user", "content": "你好，请用中文介绍你自己。"}],
    "stream": False
}

print(f"Testing /v1/chat/completions with requests at {url}...")
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        choices = res_json.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            print(f"Response (length: {len(content)}):")
            print(content)
        else:
            print("No choices in response")
            print(json.dumps(res_json, indent=2))
    else:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
