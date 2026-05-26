"""arXiv Daily Digest — 入口脚本。"""

import os
import sys
import yaml
import argparse
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

from src.fetcher import fetch_papers
from src.summarizer import screen_papers, summarize
from src.mailer import send_email


def _resolve_env(value: str) -> str:
    """解析 ${VAR} 格式的环境变量引用。"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        return os.environ.get(value[2:-1], "")
    return value


def load_config(path: str) -> dict:
    with open(path) as f:
        raw = f.read()
    # 解析 ${VAR} 引用
    import re
    for var in re.findall(r'\$\{(\w+)\}', raw):
        raw = raw.replace(f"${{{var}}}", os.environ.get(var, ""))
    return yaml.safe_load(raw)


def main():
    parser = argparse.ArgumentParser(description="arXiv Daily Digest")
    parser.add_argument(
        "-c", "--config", default="config.yaml", help="配置文件路径"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="只抓取论文不发送邮件"
    )
    parser.add_argument(
        "--skip-summarize", action="store_true", help="跳过 LLM 摘要（仅抓取）"
    )
    args = parser.parse_args()

    config_path = Path(__file__).parent / args.config
    if not config_path.exists():
        print(f"配置文件不存在: {config_path}")
        sys.exit(1)

    config = load_config(str(config_path))

    # 1. 抓取论文
    print("正在从 arXiv 抓取论文...")
    papers = fetch_papers(
        categories=config["arxiv_categories"],
        keywords=config["keywords"],
        days_back=config["days_back"],
        max_results=config["max_papers"],
    )
    print(f"抓取到 {len(papers)} 篇论文")

    if not papers:
        print("今天没有新论文。")
        return

    # 2. 标题初筛：LLM 对所有论文按标题快速打分
    if not args.skip_summarize:
        interests = config.get("research_interests", [])
        print("正在用 DeepSeek 对所有论文进行标题初筛...")
        client = Anthropic(
            api_key=config["deepseek"]["api_key"],
            base_url=config["deepseek"]["base_url"],
        )
        screen_papers(client, config["deepseek"]["model"], papers, interests)

        # 按相关性排序，取前 N 篇做详细摘要
        limit = config["deepseek"].get("max_papers_to_summarize", 6)
        papers.sort(key=lambda p: p.relevance_score, reverse=True)
        to_summarize = [p for p in papers if p.relevance_score >= 4][:limit]

        if to_summarize:
            print(f"筛选出 {len(to_summarize)} 篇相关论文，正在生成详细摘要...")
            summarize(client, config["deepseek"]["model"], to_summarize, interests)

    # 3. 发送邮件（只发送有摘要的论文）
    date = datetime.now(timezone.utc)
    digest_papers = [p for p in papers if p.summary_cn]
    if not digest_papers:
        digest_papers = papers  # 如果都没摘要，至少发所有论文
    send_email(digest_papers, config, date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
