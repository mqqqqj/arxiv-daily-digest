# arXiv Daily Digest

自动抓取 arXiv 最新论文，用 LLM 相关+摘要，每日邮件推送到邮箱。

## 功能

- 多分类抓取 arXiv 论文（AI / NLP / DB / 分布式系统 / IR / ML）
- 关键词过滤，缩小关注范围
- LLM **标题初筛** —— 对全部论文快速打分，挑出最相关的
- LLM **详细摘要** —— 问题 / 方法 / 贡献三段式中文总结
- 按相关性排序，HTML 邮件推送（支持 163 邮箱等）

## 项目结构

```
.
├── main.py                 # 入口脚本
├── config.yaml             # 配置文件（研究方向、分类、关键词等）
├── requirements.txt
├── src/
│   ├── fetcher.py          # arXiv API 抓取 + 关键词过滤
│   ├── summarizer.py       # LLM 筛选 + 摘要（DeepSeek via Anthropic SDK）
│   ├── render.py           # HTML / 纯文本邮件渲染
│   └── mailer.py           # SMTP 发送
└── .github/workflows/
    └── daily.yml           # GitHub Actions 定时任务
```

## 本地运行

```bash
pip install -r requirements.txt

# 完整流程：抓取 → 筛选 → 摘要 → 发邮件
python main.py

# 仅预览，不发送邮件
python main.py --dry-run

# 跳过 LLM 摘要
python main.py --skip-summarize
```

## 环境变量

| 变量 | 说明 |
|---|---|
| `DEEPSEEK_AUTH_TOKEN` | DeepSeek API 密钥 |
| `EMAIL_SENDER` | 发件邮箱地址 |
| `EMAIL_PASSWORD` | 邮箱 SMTP 授权码（非登录密码） |
| `EMAIL_RECEIVER` | 收件邮箱地址 |

本地运行时可通过 shell 环境变量或 `.env` 文件传入。

## GitHub Actions 定时运行

Workflow 已配置，**每天 UTC 2:00（北京时间 10:00）自动执行**，也支持手动触发。

你还需要在仓库 **Settings → Secrets and variables → Actions** 中添加 4 个 secrets：

- `DEEPSEEK_AUTH_TOKEN`
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECEIVER`

添加完成后，在 Actions 页面手动触发一次 `workflow_dispatch` 即可验证。

## 配置

编辑 `config.yaml` 即可调整：

- `research_interests` —— 研究兴趣描述（LLM 评分依据）
- `arxiv_categories` —— 拉取的 arXiv 分类
- `keywords` —— 关键词过滤
- `days_back` / `max_papers` —— 搜索范围
- `max_papers_to_summarize` —— LLM 详细摘要的论文数量上限
