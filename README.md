# GitHub Daily - 每日开源项目推送

> 每天北京时间 9 点自动搜索 GitHub 热门开源项目，使用本地 AI 生成精选总结，推送到微信群。

自动化每天搜索 GitHub 开源项目，使用本地 Ollama 进行 AI 总结，通过 PushPlus 推送到微信群。

## ✨ 特性

- 🔍 **自定义搜索** - 灵活配置搜索主题，如 AI Agent、Rust LLM 等
- 🤖 **本地 AI 总结** - 使用 Ollama 运行本地大模型，数据不离本地
- 🔒 **安全连接** - 通过 Tailscale 加密隧道访问家庭电脑
- 📱 **微信推送** - 使用 PushPlus 免费推送到微信/群聊
- 💰 **零成本** - GitHub Actions 免费额度 + 免费服务
- ⚡ **低延迟** - 本地运行 LLM，无需等待云服务

## 🏗️ 架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  GitHub Actions │────│   Tailscale      │────│  本地 Ollama    │
│  (定时调度)      │    │   (安全隧道)      │    │  (AI 总结)       │
└────────┬────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  GitHub Search  │
│  API            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PushPlus       │
│  (微信推送)      │
└─────────────────┘
```

## 架构图

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  GitHub Actions │────│   Tailscale      │────│  本地 Ollama    │
│  (定时调度)      │    │   (安全隧道)      │    │  (AI 总结)       │
└────────┬────────┘    └──────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│  GitHub Search  │
│  API            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PushPlus       │
│  (微信推送)      │
└─────────────────┘
```

## 文件结构

```
.
├── search_and_summarize.py    # 主脚本：搜索 + AI 总结 + 推送
├── .github/
│   └── workflows/
│       └── daily-interest.yml  # Actions 定时任务
├── README.md
└── requirements.txt
```

## 准备工作

### 1. GitHub 配置

#### 1.1 创建 Personal Access Token (PAT)
1. 访问 GitHub Settings → Developer settings → Personal access tokens → Classic
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 复制生成的 token，保存好（只会显示一次）

#### 1.2 配置仓库 Secrets
在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `REPO_TOKEN` | GitHub PAT | `ghp_xxxxxxxxxxxx` |
| `PUSHPLUS_TOKEN` | PushPlus token | 见下方获取步骤 |
| `PUSHPLUS_GROUP` | 微信群组编码（可选） | `xxxxx` |
| `TAILSCALE_AUTHKEY` | Tailscale 临时认证 key | `tskey-auth-xxxxx` |

### 2. 获取 PushPlus Token

1. 访问 https://www.pushplus.plus/
2. 微信扫码登录
3. 在"一对一推送"获取 token
4. 如果要发群聊：在"群组管理"创建群组，获取 group code

### 3. 配置 Tailscale

#### 3.1 安装 Tailscale（家用电脑）
1. 访问 https://tailscale.com/download 下载安装
2. 登录你的 Tailscale 账号
3. 在 admin 面板 (https://login.tailscale.com/admin) 启用 MagicDNS

#### 3.2 生成 Auth Key
1. 访问 https://login.tailscale.com/admin/settings/keys
2. Generate auth key → 勾选 Ephemeral → Generate
3. 复制 key，保存到 GitHub Secrets

#### 3.3 确认主机名
在 Tailscale admin 面板查看你的设备主机名（本配置中使用的是 `popos`）

### 4. 配置本地 Ollama

#### 4.1 安装 Ollama
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows: 下载安装包
```

#### 4.2 拉取模型
```bash
ollama pull qwen3.5:4b
```

#### 4.3 启动服务（监听所有接口）
```bash
# Linux
export OLLAMA_HOST=0.0.0.0
ollama serve

# macOS
launchctl setenv OLLAMA_HOST "0.0.0.0"
ollama serve

# Windows (PowerShell)
$env:OLLAMA_HOST="0.0.0.0"
ollama serve
```

#### 4.4 设置开机自启

**Linux (systemd):**
```bash
sudo systemctl edit ollama.service
# 添加：
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
sudo systemctl restart ollama
```

**macOS (launchd):**
```bash
brew services stop ollama
launchctl setenv OLLAMA_HOST "0.0.0.0"
brew services start ollama
```

**Windows (任务计划程序):**
创建一个开机启动的任务，运行：
```
powershell -Command "$env:OLLAMA_HOST='0.0.0.0'; ollama serve"
```

## 本地测试

### 安装依赖
```bash
pip install requests openai
```

### 设置环境变量
```bash
export REPO_TOKEN="ghp_xxxxx"
export PUSHPLUS_TOKEN="your_token"
```

### 运行脚本
```bash
python search_and_summarize.py
```

## 自定义搜索主题

编辑 `search_and_summarize.py` 中的 `QUERIES` 列表：

### 🎯 默认配置（AI 项目精选）

当前已预设 4 个 AI 相关主题，自动筛选近 7 天热门新项目：

| 主题 | 搜索关键词 | Star 阈值 | 数量 |
|------|-----------|----------|------|
| **AI 热门新项目** | AI / artificial intelligence / machine learning / deep learning / neural network | ≥50 | 15 个 |
| **LLM/生成式 AI** | LLM / large language model / language model / generative AI / AIGC | ≥30 | 10 个 |
| **AI Agent** | AI agent / multi-agent / autonomous agent / intelligent agent | ≥20 | 8 个 |
| **RAG/向量数据库** | RAG / retrieval augmented / vector database / embedding | ≥20 | 6 个 |

所有主题均限定：**2026-03-01 之后创建**、**排除 fork 项目**

### 🔧 添加自定义主题

```python
QUERIES = [
    # ... 默认主题
    {
        "q": '("fastapi" OR "async api") created:>=2026-03-01 stars:>=100',
        "label": "Python Web 框架",
        "max_items": 5
    },
]
```

### GitHub Search 语法速查

| 语法 | 说明 | 示例 |
|------|------|------|
| `created:>=YYYY-MM-DD` | 创建日期 | `created:>=2026-03-01` |
| `stars:>=N` / `stars>N` | Star 数量 | `stars:>=50` |
| `language:xxx` | 编程语言 | `language:rust` |
| `-is:fork` | 排除 fork | `-is:fork` |
| `-archived` | 排除归档 | `-archived` |
| `"..."` | 精确匹配 | `"machine learning"` |
| `OR` | 逻辑或 | `(A OR B)` |
| `in:name,description` | 搜索范围 | `in:README` |

## 故障排查

### Ollama 连接失败
```bash
# 检查 Tailscale 连接
tailscale status

# 检查 Ollama 服务
curl http://localhost:11434/api/tags

# 检查防火墙
sudo ufw allow 11434/tcp  # Linux
```

### GitHub API 限流
- 未认证：每小时 10 次
- 已认证：每小时 5000 次
- 解决方案：确保配置了 `GITHUB_TOKEN`

### PushPlus 推送失败
- 检查 token 是否正确
- 检查群组编码（如果发群）
- 访问 PushPlus 官网查看推送日志

## 修改调度时间

编辑 `.github/workflows/daily-interest.yml`:

```yaml
on:
  schedule:
    - cron: '0 1 * * *'   # 改为其他时间
```

Cron 格式：`分 时 日 月 周`（UTC 时间）

常用时间：
- `0 1 * * *` - 每天 09:00（北京）
- `0 0 * * *` - 每天 08:00（北京）
- `0 */6 * * *` - 每 6 小时

## 成本说明

- GitHub Actions: 免费（每月 2000 分钟）
- Tailscale: 免费（支持 3 用户 + 100 设备）
- PushPlus: 免费
- Ollama: 仅需家用电脑电费

## License

MIT
