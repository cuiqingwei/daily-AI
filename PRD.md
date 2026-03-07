# 每天9点推送GitHub开源项目到微信群的完整方案（自定义搜索 + AI总结 + 本地LLM）

## 概述

本方案使用**GitHub Actions**自动化每天北京时间9:00搜索用户关心的GitHub开源项目（通过GitHub Search API），然后使用**本地Ollama**（运行在家用电脑上，通过**Tailscale**安全映射）生成AI总结，最后通过**PushPlus**推送Markdown格式内容到指定微信群。

- **优势**：免费/低成本、稳定、私密（数据不离本地）、自定义搜索（如AI Agent、Rust LLM等主题）。
- **适用人群**：对GitHub开源感兴趣的用户，想自动化推送+智能总结。
- **成本**：基本0元（GitHub Actions免费额度够用，Tailscale免费版支持）。
- **难度**：★★★☆☆（需有基本编程知识和一台常开电脑运行Ollama）。
- **时间**：初次设置30-60分钟。
- **当前日期**：2026年3月（方案基于此时间点优化）。

## 准备工作

### 1. GitHub侧
- 创建一个GitHub仓库（新建或Fork）。
- 生成Personal Access Token (PAT)：GitHub Settings → Developer settings → Personal access tokens → Classic → 选`repo`权限 → 复制token。
- 设置仓库Secrets（Settings → Secrets and variables → Actions）：
  - `GITHUB_TOKEN`：你的PAT。
  - `PUSHPLUS_TOKEN`：PushPlus token（见下）。
  - `PUSHPLUS_GROUP`：微信群组编码（可选，如果发群）。
  - `TAILSCALE_AUTHKEY`：Tailscale ephemeral auth key（见Tailscale部分）。

### 2. PushPlus（微信推送）
- 访问 https://www.pushplus.plus/。
- 微信扫码登录 → 获取“一对一推送”或“群组推送”的token。
- 如果发群：在“群组管理”添加群，获取group code。

### 3. Tailscale（安全映射本地Ollama）
- 安装Tailscale：https://tailscale.com/download（家用电脑上安装）。
- 登录Tailscale账号，启用MagicDNS（admin面板 → DNS → Enable MagicDNS）。
- 生成ephemeral auth key：admin面板 → Settings → Keys → Generate auth key → Ephemeral → 复制key。
- 记下家用电脑的Tailscale主机名（e.g., `ollama-pc`）。

### 4. 本地Ollama（家用电脑运行LLM）
- 安装Ollama：https://ollama.com/download。
- 拉取模型：`ollama pull qwen2.5:14b`（或适合你硬件的模型，如llama3.2:3b）。
- 启动服务并监听所有接口：
  - Windows：`set OLLAMA_HOST=0.0.0.0` → `ollama serve`。
  - Linux/macOS：`export OLLAMA_HOST=0.0.0.0` → `ollama serve`。
- 建议设为开机自启（使用systemd或Windows任务计划）。

### 5. 自定义搜索查询
在脚本中修改`QUERIES`列表，例如：
- AI Agent：`("AI agent" OR "multi-agent" OR "autonomous agent") created:>=2026-03-01 stars:>=20 -is:fork`。
- Rust LLM：`rust (llm OR inference OR "large language model") stars:>50 created:>=2026-02-20`。
- 支持高级过滤：language、stars、created等。

## 仓库文件结构

```
仓库根目录/
├── search_and_summarize.py    # 主脚本：搜索 + AI总结 + 推送
└── .github/
    └── workflows/
        └── daily-interest.yml  # Actions workflow
```

### search_and_summarize.py（核心脚本）

```python
# -*- coding: utf-8 -*-
import requests
import os
import json
import datetime
from typing import List, Dict
from openai import OpenAI  # 用于Ollama的OpenAI兼容接口

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
PUSHPLUS_GROUP = os.getenv("PUSHPLUS_GROUP", "")
LLM_BASE_URL = "http://ollama-pc:11434/v1"  # Tailscale域名 + 端口
LLM_MODEL = "qwen2.5:14b"  # 你本地模型

# 自定义查询（修改这里）
QUERIES = [
    {
        "q": '("AI agent" OR "multi-agent" OR "autonomous agent") created:>=2026-03-01 stars:>=20 -is:fork',
        "label": "AI Agent 新项目",
        "max_items": 8
    },
    {
        "q": 'rust (llm OR inference OR "large language model") stars:>50 created:>=2026-02-20',
        "label": "Rust LLM/推理相关",
        "max_items": 6
    },
    # 添加更多...
]

def github_search(q: str, sort="stars", order="desc", per_page=30) -> List[Dict]:
    url = "https://api.github.com/search/repositories"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    params = {"q": q, "sort": sort, "order": order, "per_page": per_page}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"GitHub API error: {resp.status_code} {resp.text}")
        return []
    return resp.json().get("items", [])

def ai_summarize_batch(repos: List[Dict], query_label: str) -> str:
    if not repos:
        return ""

    items_text = ""
    for r in repos:
        name = r["full_name"]
        desc = (r.get("description") or "无描述").strip()[:180]
        stars = r["stargazers_count"]
        url = r["html_url"]
        lang = r.get("language", "未知")
        items_text += f"- **{name}** ({lang}) — ★{stars}  {desc[:120]}{'...' if len(desc)>120 else ''}\n  {url}\n"

    prompt = f"""你是一个GitHub开源项目研究员。
今天是{datetime.date.today()}。
用户关注主题：{query_label}

以下是最新匹配的一些仓库（按star降序）：

{items_text}

请为用户写一段**简洁、有吸引力**的中文总结（150-280字），包含：
1. 整体趋势一句话
2. 挑2-4个最有潜力的项目，讲清亮点、创新点、为什么值得关注
3. 用自然、兴奋但不夸张的语气，像朋友推荐

输出纯文本，不要markdown标题或列表符号。"""

    client = OpenAI(base_url=LLM_BASE_URL, api_key="ollama")  # 兼容接口
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return "AI总结失败（API问题），请查看下方原始列表。\n\n" + items_text

def send_to_wechat(title: str, content: str):
    if not PUSHPLUS_TOKEN:
        print("缺少 PUSHPLUS_TOKEN")
        return
    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "txt",  # 或 markdown
    }
    if PUSHPLUS_GROUP:
        data["topic"] = PUSHPLUS_GROUP
    requests.post(url, json=data)

if __name__ == "__main__":
    today = datetime.date.today().strftime("%Y-%m-%d")
    full_content = f"每日开源精选 {today}（自定义主题）\n\n"

    for query in QUERIES:
        items = github_search(query["q"], per_page=query["max_items"] * 2)[:query["max_items"]]
        if not items:
            continue

        summary = ai_summarize_batch(items, query["label"])
        full_content += f"【{query['label']}】\n{summary}\n\n"

    full_content += "\n数据来源于GitHub Search API | 如有感兴趣的项目，欢迎去star支持作者～"

    send_to_wechat(f"每日开源精选 {today}", full_content)
    print("推送完成")
```

### daily-interest.yml（GitHub Actions Workflow）

```yaml
name: Daily Custom GitHub Search + AI Summary

on:
  schedule:
    - cron: '0 1 * * *'   # UTC 01:00 → 北京09:00
  workflow_dispatch:

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Connect to Tailscale
        uses: tailscale/github-action@v4
        with:
          authkey: ${{ secrets.TAILSCALE_AUTHKEY }}

      - name: Wait for Tailscale to be ready
        run: sleep 8

      - name: Test connection to home Ollama
        run: curl -v http://ollama-pc:11434/api/tags  # 替换为你的主机名

      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install requests openai  # 加 openai client

      - name: Run search & push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PUSHPLUS_TOKEN: ${{ secrets.PUSHPLUS_TOKEN }}
          PUSHPLUS_GROUP: ${{ secrets.PUSHPLUS_GROUP }}
        run: python search_and_summarize.py
```

## 测试与运行

1. 手动触发：仓库 → Actions → 选workflow → Run workflow。
2. 检查日志：看是否连接Tailscale、调用Ollama、推送成功。
3. 调试：如果Ollama连接失败，检查防火墙、端口、Tailscale状态。

## 注意事项与扩展

- **稳定性**：家用电脑需常开；Tailscale加密安全，无公网暴露。
- **成本**：Ollama用电费；Actions免费（每月2000分钟）。
- **扩展**：
  - 改模型：用更大模型提升总结质量。
  - 加查询：扩展QUERIES支持更多主题。
  - 备份：如果本地Ollama不可用，可fallback到云LLM（加Secrets）。
- **常见问题**：
  - 连接拒：确认Ollama监听0.0.0.0。
  - Rate limit：GitHub API每天限额，少量查询无问题。