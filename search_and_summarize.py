# -*- coding: utf-8 -*-
"""
每日 GitHub 开源项目搜索 + AI 总结 + 微信推送脚本
使用本地 Ollama（通过 Tailscale 安全访问）进行 AI 总结
"""
import requests
import os
import json
import datetime
from typing import List, Dict
from openai import OpenAI

# ============== 配置区域 ==============
# 环境变量（GitHub Secrets）
REPO_TOKEN = os.getenv("REPO_TOKEN", "")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
PUSHPLUS_GROUP = os.getenv("PUSHPLUS_GROUP", "")

# Tailscale 配置（通过环境变量 OLLAMA_HOST_IP 覆盖）
TAILSCALE_HOST = os.getenv("OLLAMA_HOST_IP", "popos")  # 家用电脑的 Tailscale IP/主机名
LLM_BASE_URL = f"http://{TAILSCALE_HOST}:11434/v1"
LLM_MODEL = "qwen3.5:4b"  # 本地 Ollama 模型

# 自定义搜索查询（修改这里添加更多主题）
QUERIES = [
    {
        "q": 'topic:ai',
        "label": "AI 热门项目 Top 10",
        "max_items": 10
    },
]
# ======================================


def github_search(q: str, sort: str = "stars", order: str = "desc", per_page: int = 30) -> List[Dict]:
    """
    使用 GitHub Search API 搜索仓库

    Args:
        q: 搜索查询字符串
        sort: 排序字段（stars, forks, updated 等）
        order: 排序方向（asc, desc）
        per_page: 每页数量

    Returns:
        仓库列表
    """
    url = "https://api.github.com/search/repositories"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {REPO_TOKEN}" if REPO_TOKEN else "",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    params = {"q": q, "sort": sort, "order": order, "per_page": per_page}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"GitHub API error: {resp.status_code} {resp.text}")
            return []
        return resp.json().get("items", [])
    except Exception as e:
        print(f"GitHub search error: {e}")
        return []


def ai_summarize_batch(repos: List[Dict], query_label: str) -> str:
    """
    使用本地 Ollama 对仓库列表进行 AI 总结

    Args:
        repos: GitHub 仓库列表
        query_label: 查询标签/主题

    Returns:
        AI 生成的总结文本
    """
    if not repos:
        return ""

    # 构建项目列表文本
    items_text = ""
    for r in repos:
        name = r["full_name"]
        desc = (r.get("description") or "无描述").strip()[:180]
        stars = r["stargazers_count"]
        url = r["html_url"]
        lang = r.get("language", "未知")
        items_text += f"- **{name}** ({lang}) — ★{stars}  {desc[:120]}{'...' if len(desc)>120 else ''}\n  {url}\n"

    today = datetime.date.today().strftime("%Y-%m-%d")
    prompt = f"""你是一个 GitHub 开源项目研究员。
今天是{today}。
用户关注主题：{query_label}

以下是最新匹配的一些仓库（按 star 降序）：

{items_text}

请为用户写一段**简洁、有吸引力**的中文总结（150-280 字），包含：
1. 整体趋势一句话
2. 挑 2-4 个最有潜力的项目，讲清亮点、创新点、为什么值得关注
3. 用自然、兴奋但不夸张的语气，像朋友推荐

输出纯文本，不要 markdown 标题或列表符号。"""

    try:
        client = OpenAI(base_url=LLM_BASE_URL, api_key="ollama")
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
            timeout=120
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM error: {e}")
        return f"AI 总结失败（API 问题：{e}），请查看下方原始列表。\n\n{items_text}"


def send_to_wechat(title: str, content: str) -> bool:
    """
    通过 PushPlus 发送消息到微信

    Args:
        title: 消息标题
        content: 消息内容

    Returns:
        是否发送成功
    """
    if not PUSHPLUS_TOKEN:
        print("缺少 PUSHPLUS_TOKEN，跳过推送")
        return False

    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "txt",
    }
    if PUSHPLUS_GROUP:
        data["topic"] = PUSHPLUS_GROUP

    try:
        resp = requests.post(url, json=data, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 200:
                print("推送成功")
                return True
            else:
                print(f"推送失败：{result}")
        else:
            print(f"推送请求失败：{resp.status_code}")
    except Exception as e:
        print(f"推送错误：{e}")
    return False


def main():
    """主函数"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    full_content = f"# 每日开源精选 {today}（自定义主题）\n\n"

    print(f"开始处理 {len(QUERIES)} 个查询主题...")

    for query in QUERIES:
        label = query["label"]
        print(f"  搜索：{label}")

        # 搜索 GitHub（获取 2 倍数量用于后续筛选）
        items = github_search(query["q"], per_page=query["max_items"] * 2)
        if not items:
            print(f"    无结果")
            continue

        # 取前 N 个
        items = items[:query["max_items"]]
        print(f"    找到 {len(items)} 个项目")

        # AI 总结
        print(f"    生成 AI 总结...")
        summary = ai_summarize_batch(items, label)

        full_content += f"## 【{label}】\n{summary}\n\n"
        print(f"    完成")

    full_content += "---\n数据来源于 GitHub Search API | 如有感兴趣的项目，欢迎去 star 支持作者～"

    print("\n推送内容预览（前 200 字）:")
    print(full_content[:200] + "...")

    # 发送到微信
    send_to_wechat(f"每日开源精选 {today}", full_content)
    print("\n处理完成")


if __name__ == "__main__":
    main()
