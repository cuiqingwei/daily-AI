import os
import datetime
import requests
from openai import OpenAI
import httpx

TAILSCALE_HOST = "mbp"
LLM_BASE_URL = f"http://{OLLAMA_HOSTNAME}:11434/v1"
LLM_MODEL = "qwen3.5:4b"

prompt = "你是一个专业的 GitHub 开源项目分析师。今天是 2026-03-08。请写一段中文调研简报，说明 AI 领域的最新趋势。直接输出内容，不要使用 markdown 标题。"

print(f"Testing connection to {LLM_BASE_URL}...")
try:
    http_client = httpx.Client(trust_env=False)
    client = OpenAI(base_url=LLM_BASE_URL, api_key="none", http_client=http_client)
    
    print(f"Sending request to model {LLM_MODEL}...")
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=800,
        timeout=120.0
    )
    content = response.choices[0].message.content
    print(f"Response received (length: {len(content)}):")
    print("-" * 20)
    print(content)
    print("-" * 20)
except Exception as e:
    print(f"Error: {e}")
