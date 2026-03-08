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
TAILSCALE_HOST = os.getenv("OLLAMA_HOST_IP", "popos")  # 默认使用 popos 主机
LLM_BASE_URL = f"http://{TAILSCALE_HOST}:11434/v1"
LLM_MODEL = "qwen3.5:4b"  # 本地 Ollama 模型

# 自定义搜索查询（修改这里添加更多主题）
QUERIES = [
    {
        "q": 'topic:ai',
        "label": "AI 热门项目 Top 10",
        "max_items": 5
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

    # 构建项目列表文本（原始内容提供给 AI）
    items_text = ""
    for r in repos:
        name = r["full_name"]
        desc = (r.get("description") or "无描述").strip()[:180]
        stars = r["stargazers_count"]
        url = r["html_url"]
        lang = r.get("language", "未知")
        items_text += f"项目: {name} (语言: {lang}, Star: {stars})\n描述: {desc}\n链接: {url}\n\n"

    today = datetime.date.today().strftime("%Y-%m-%d")
    prompt = f"""你是一个专业的 GitHub 开源项目分析师。今天是 {today}。
请根据以下项目信息，写一份中文调研简报。

项目列表：
{items_text}

任务要求：
1. 概括今日开源趋势（中文，30字以内）。
2. 推荐 2-3 个核心亮点项目，使用中文说明理由。
3. 严禁输出任何英文总结，必须全部为中文。
4. 全文约 200 字。

直接开始输出简报正文："""

    summary_content = ""
    # 使用与测试脚本一致的请求方式
    url = f"{LLM_BASE_URL}/chat/completions"
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "stream": False
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=150)
        if resp.status_code == 200:
            result = resp.json()
            choices = result.get("choices", [])
            if choices:
                summary_content = choices[0].get("message", {}).get("content", "").strip()
            else:
                summary_content = result.get("message", {}).get("content", "").strip()
        else:
            print(f"    [警告] Ollama 接口返回错误: {resp.status_code}")
    except Exception as e:
        print(f"    [警告] AI 总结生成异常: {e}")

    if not summary_content:
        summary_content = "*(AI 总结生成失败，请查阅下方列表)*"

    # 构建最终输出
    header = f"### 🤖 AI 项目简报 ({today})\n"
    footer = "\n\n### 🔗 原始项目列表\n"
    ref_list = ""
    for r in repos:
        ref_list += f"- **{r['full_name']}** (★{r['stargazers_count']}): {r['html_url']}\n"

    return f"{header}{summary_content}{footer}{ref_list}"


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
