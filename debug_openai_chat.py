from openai import OpenAI
import httpx

url = "http://popos:1234/v1"
try:
    http_client = httpx.Client(trust_env=False)
    client = OpenAI(base_url=url, api_key="none", http_client=http_client)
    print(f"Testing OpenAI library with Chat at {url}...")
    response = client.chat.completions.create(
        model="google/gemma-4-e2b",
        messages=[{"role": "user", "content": "你好，请用中文介绍你自己。"}],
        temperature=0.5,
        max_tokens=600
    )
    content = response.choices[0].message.content
    print(f"Response (length: {len(content)}):")
    print(content)
except Exception as e:
    print(f"Error: {e}")
