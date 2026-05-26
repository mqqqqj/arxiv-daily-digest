"""arXiv 论文抓取：按分类搜索最新论文，本地关键词过滤。"""

import time
import arxiv
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    url: str
    pdf_url: str
    published: datetime
    categories: list[str]
    relevance_score: float = 0.0
    summary_cn: str = ""


def _matches_keywords(paper: Paper, keywords: list[str]) -> bool:
    """检查论文标题或摘要是否命中关键词。"""
    text = (paper.title + " " + paper.abstract).lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False


def fetch_papers(
    categories: list[str],
    keywords: list[str],
    days_back: int = 1,
    max_results: int = 80,
) -> list[Paper]:
    """从 arXiv 分类抓取最新论文，本地关键词过滤。"""
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    client = arxiv.Client(page_size=50, delay_seconds=12)

    all_papers: dict[str, Paper] = {}

    for idx, cat in enumerate(categories):
        if idx > 0:
            time.sleep(15)

        for attempt in range(3):
            try:
                search = arxiv.Search(
                    query=f"cat:{cat}",
                    max_results=max(20, max_results // len(categories)),
                    sort_by=arxiv.SortCriterion.SubmittedDate,
                )
                for result in client.results(search):
                    if result.published.replace(tzinfo=timezone.utc) < since:
                        continue
                    if result.entry_id in all_papers:
                        continue
                    all_papers[result.entry_id] = Paper(
                        arxiv_id=result.entry_id.split("/")[-1],
                        title=result.title.strip(),
                        authors=[a.name for a in result.authors],
                        abstract=result.summary.strip(),
                        url=result.entry_id,
                        pdf_url=result.pdf_url,
                        published=result.published,
                        categories=list(result.categories),
                    )
                print(f"  {cat}: 抓取成功")
                break
            except Exception as e:
                print(f"  {cat} (尝试 {attempt+1}/3): {e}")
                time.sleep(20)

    papers = list(all_papers.values())

    if keywords:
        papers = [p for p in papers if _matches_keywords(p, keywords)]

    return sorted(papers, key=lambda p: p.published, reverse=True)
