"""HTML 邮件渲染。"""

from datetime import datetime
from .fetcher import Paper


STYLE = """
body { margin:0; padding:0; background:#f5f5f5; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }
.container { max-width:680px; margin:0 auto; background:#fff; }
.header { background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%); padding:32px 24px; text-align:center; }
.header h1 { color:#fff; margin:0 0 8px; font-size:24px; }
.header .date { color:#a0a0b8; font-size:14px; }
.stats { display:flex; justify-content:center; gap:24px; padding:20px 24px; background:#fafafa; border-bottom:1px solid #eee; }
.stat { text-align:center; }
.stat .num { font-size:28px; font-weight:700; color:#1a1a2e; }
.stat .label { font-size:12px; color:#888; margin-top:4px; }
.paper-list { padding:24px; }
.paper { padding:20px 0; border-bottom:1px solid #eee; }
.paper:last-child { border-bottom:none; }
.paper .title { font-size:16px; font-weight:600; margin:0 0 8px; }
.paper .title a { color:#1a1a2e; text-decoration:none; }
.paper .title a:hover { color:#4a6cf7; }
.paper .meta { font-size:12px; color:#888; margin-bottom:8px; }
.paper .score { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; color:#fff; }
.paper .score.high { background:#22c55e; }
.paper .score.medium { background:#f59e0b; }
.paper .score.low { background:#94a3b8; }
.paper .summary { font-size:14px; color:#444; line-height:1.6; margin:8px 0; }
.paper .links { font-size:12px; }
.paper .links a { color:#4a6cf7; text-decoration:none; margin-right:12px; }
.footer { text-align:center; padding:24px; font-size:12px; color:#aaa; border-top:1px solid #eee; }
"""


def render_html(papers: list[Paper], date: datetime) -> str:
    """生成 HTML 邮件内容。"""
    sorted_papers = sorted(papers, key=lambda p: p.relevance_score, reverse=True)

    papers_html = ""
    for p in sorted_papers:
        score = p.relevance_score
        if score >= 7:
            score_class = "high"
        elif score >= 4:
            score_class = "medium"
        else:
            score_class = "low"

        authors = ", ".join(p.authors[:4])
        if len(p.authors) > 4:
            authors += " et al."

        summary = p.summary_cn or p.abstract[:400] + "..."

        papers_html += f"""
<div class="paper">
    <h3 class="title"><a href="{p.url}">{p.title}</a></h3>
    <div class="meta">{authors} &nbsp;·&nbsp; {", ".join(p.categories[:3])} &nbsp;·&nbsp; <span class="score {score_class}">{score}/10</span></div>
    <div class="summary">{summary}</div>
    <div class="links">
        <a href="{p.url}">arXiv</a>
        <a href="{p.pdf_url}">PDF</a>
    </div>
</div>"""

    high_count = sum(1 for p in sorted_papers if p.relevance_score >= 7)
    mid_count = sum(1 for p in sorted_papers if 4 <= p.relevance_score < 7)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body>
<div class="container">
    <div class="header">
        <h1>arXiv Daily Digest</h1>
        <div class="date">{date.strftime('%Y-%m-%d')} · agent memory & vector retrieval</div>
    </div>
    <div class="stats">
        <div class="stat"><div class="num">{len(sorted_papers)}</div><div class="label">总论文</div></div>
        <div class="stat"><div class="num">{high_count}</div><div class="label">高相关 (≥7)</div></div>
        <div class="stat"><div class="num">{mid_count}</div><div class="label">中等相关 (4-6)</div></div>
    </div>
    <div class="paper-list">{papers_html}
    </div>
    <div class="footer">
        arXiv Daily Digest · 自动生成于 {date.strftime('%Y-%m-%d %H:%M UTC')}<br>
        Powered by DeepSeek AI
    </div>
</div>
<style>{STYLE}</style>
</body>
</html>"""


def render_plain(papers: list[Paper], date: datetime) -> str:
    """生成纯文本备用版本。"""
    sorted_papers = sorted(papers, key=lambda p: p.relevance_score, reverse=True)
    lines = [
        f"学术日报 — {date.strftime('%Y-%m-%d')}",
        f"研究方向: Agent Memory & Vector Search",
        f"共 {len(sorted_papers)} 篇论文\n",
    ]
    for i, p in enumerate(sorted_papers):
        lines.append(f"{'='*60}")
        lines.append(f"[{p.relevance_score}/10] {p.title}")
        lines.append(f"作者: {', '.join(p.authors[:4])}")
        lines.append(f"摘要: {p.summary_cn or p.abstract[:400]}...")
        lines.append(f"链接: {p.url}\n")
    return "\n".join(lines)
