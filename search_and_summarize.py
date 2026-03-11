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

# ============== 配置区域 ==============
# 环境变量（GitHub Secrets）
REPO_TOKEN = os.getenv("REPO_TOKEN", "")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "")
PUSHPLUS_GROUP = os.getenv("PUSHPLUS_GROUP", "")
# 环境变量（GitHub Variables）
OLLAMA_HOSTNAME = os.getenv("OLLAMA_HOSTNAME", "mbp")

# Local LLM主机配置
LLM_BASE_URL = f"http://{OLLAMA_HOSTNAME}:11434/v1"
LLM_MODEL = "qwen3.5:4b"  # 本地 Ollama 模型

# 自定义搜索查询（修改这里添加更多主题）
QUERIES = [
    {
        "q": 'topic:ai',
        "label": "ai",
        "max_items": 5
    },
]

# HTML 模板
HTML_TEMPLATE = """
<div style="max-width: 650px; margin: 0 auto; font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;">
  <!-- 顶部标题栏 -->
  <div style="background: linear-gradient(120deg, #4361ee 0%, #3a0ca3 100%); color: #fff; padding: 20px 24px; border-radius: 12px 12px 0 0;">
    <h2 style="margin: 0; font-size: 20px; font-weight: 600;">每日开源精选 {date}</h2>
    <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.9;">topic: {topic} | Gary · {datetime}</p>
  </div>

  <!-- 主体内容区 -->
  <div style="background: #fff; padding: 24px; border-radius: 0 0 12px 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08);">
    <!-- AI项目简报 -->
    <div style="margin-bottom: 28px;">
      <h3 style="color: #2b2d42; margin: 0 0 12px; font-size: 16px; font-weight: 600;">
        🤖 AI项目简报
      </h3>
      <p style="color: #4a4e69; line-height: 1.7; font-size: 14px; margin: 0;">
        {ai_summary}
        <br><span style="color: #9a8c98; font-size: 12px; display: block; margin-top: 8px;">--- 由家中 Local LLM（{llm_model}）总结</span>
      </p>
    </div>

    <!-- 项目列表 -->
    <div>
      <h3 style="color: #2b2d42; margin: 0 0 4px; font-size: 16px; font-weight: 600;">
        🔗 热门开源项目
      </h3>
      <div style="display: flex; flex-direction: column; gap: 3px;">
        {items_html}
      </div>
    </div>

    <!-- 底部备注 -->
    <p style="color: #9a8c98; font-size: 12px; text-align: center; margin: 24px 0 0; padding-top: 16px; border-top: 1px solid #e5e5e5;">
      数据来源于 GitHub Search API | 如有感兴趣的项目，欢迎去 star 支持作者 ~
    </p>
  </div>
</div>
"""

ITEM_TEMPLATE = """
        <div style="padding: 16px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #4361ee; margin-bottom: 3px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <strong style="color: #2b2d42; font-size: 14px;">{full_name}</strong>
            <span style="color: #f77f00; font-size: 13px;">★ {stars}</span>
          </div>
          <a href="{html_url}" style="color: #4361ee; font-size: 13px; text-decoration: none;">
            {html_url}
          </a>
        </div>
"""
# ======================================


def github_search(q: str, sort: str = "stars", order: str = "desc", per_page: int = 30) -> List[Dict]:
    """使用 GitHub Search API 搜索仓库"""
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


def ai_summarize_batch(repos: List[Dict]) -> str:
    """使用本地 Ollama 对仓库列表进行 AI 总结，仅返回总结正文"""
    if not repos:
        return ""

    # 1. 预热模型
    try:
        requests.post(f"http://{OLLAMA_HOSTNAME}:11434/api/generate", json={"model": LLM_MODEL, "keep_alive": "5m"}, timeout=10)
    except:
        pass

    # 2. 构建输入
    # 增加项目数量到 5 个以匹配推送
    ai_input_text = ""
    for r in repos[:5]:
        name = r["full_name"]
        desc = (r.get("description") or "无描述").strip()[:100]
        ai_input_text += f"项目: {name}\n说明: {desc}\n\n"

    today = datetime.date.today().strftime("%Y-%m-%d")
    prompt = f"你是 GitHub 研究员。今天 {today} 有以下项目：\n{ai_input_text}\n请用中文写一段 100 字左右的趋势简报，点出亮点。直接输出正文。"

    # 3. 使用原生 Ollama 接口
    url = f"http://{OLLAMA_HOSTNAME}:11434/api/chat"
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }

    summary_content = ""
    try:
        with requests.post(url, json=payload, timeout=240, stream=True) as resp:
            if resp.status_code == 200:
                print("    [生成中] ", end="", flush=True)
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        summary_content += content
                        print(".", end="", flush=True)
                        if chunk.get("done"):
                            break
                print(" 完成")
            else:
                print(f"    [警告] Ollama 状态码: {resp.status_code}")
    except Exception as e:
        print(f"\n    [警告] AI 总结超时或错误: {e}")

    if not summary_content:
        summary_content = "今日 AI 总结繁忙，请直接阅读下方精选项目。"

    return summary_content


def send_to_wechat(title: str, content: str) -> bool:
    """通过 PushPlus 发送消息到微信 (使用 HTML 模板)"""
    if not PUSHPLUS_TOKEN:
        print("缺少 PUSHPLUS_TOKEN，跳过推送")
        return False

    url = "http://www.pushplus.plus/send"
    data = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": content,
        "template": "html",
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
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"开始处理 {len(QUERIES)} 个查询主题...")

    for query in QUERIES:
        topic_label = query["label"]
        print(f"  搜索：{topic_label}")

        items = github_search(query["q"], per_page=query["max_items"])
        if not items:
            print(f"    无结果")
            continue

        print(f"    找到 {len(items)} 个项目")

        # 生成 AI 总结
        print(f"    生成 AI 总结...")
        ai_summary = ai_summarize_batch(items)

        # 生成项目列表 HTML
        items_html = ""
        for item in items:
            items_html += ITEM_TEMPLATE.format(
                full_name=item["full_name"],
                stars=item["stargazers_count"],
                html_url=item["html_url"]
            )

        # 组装完整的 HTML 页面
        full_html = HTML_TEMPLATE.format(
            date=today_str,
            topic=topic_label,
            datetime=datetime_str,
            ai_summary=ai_summary,
            llm_model=LLM_MODEL,
            items_html=items_html
        )

        print("\n推送内容预览（前 200 字）:")
        print(full_html[:200] + "...")

        # 发送到微信
        send_to_wechat(f"每日开源精选 {today_str}", full_html)
        print(f"    完成")

    print("\n所有任务处理完成")


if __name__ == "__main__":
    main()
