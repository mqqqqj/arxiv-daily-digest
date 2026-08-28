"""DeepSeek LLM 摘要 + 相关性评分（通过 Anthropic SDK 调用）。"""

import json
import re
from anthropic import Anthropic
from .fetcher import Paper


SCREEN_PROMPT = """你是学术论文评审专家。下面有若干篇 arXiv 论文的标题。
根据每篇论文的标题，评估它与以下研究兴趣的相关性，给出 1-10 的整数评分：
{interests}
与上述方向直接相关的论文给 7-10 分，部分相关 4-6 分，不相关 1-3 分。
只输出 JSON，格式如下，不要任何其他文字：
```json
[
  {{"arxiv_id": "论文ID", "relevance_score": 8}},
  ...
]
```

论文列表：
"""


PROMPT = """你是学术论文评审专家。下面有若干篇 arXiv 论文的标题和摘要。
你的任务：
1. 对每篇论文，用中文写摘要（150-300字，禁止用英文），必须包含以下三部分：
   - 研究问题：这篇论文要解决什么核心问题？
   - 方法：作者用了什么技术方案、模型架构或算法？
   - 贡献/发现：主要结论或创新点是什么？
2. 根据论文与以下研究兴趣的相关性，给出 1-10 的整数评分：
{interests}
   与上述方向直接相关的论文给 7-10 分，部分相关 4-6 分，不相关 1-3 分。
3. 只输出 JSON，格式如下，不要任何其他文字：
```json
[
  {{"arxiv_id": "论文ID", "summary_cn": "中文摘要（150-300字，包含问题/方法/贡献三个部分）", "relevance_score": 8}},
  ...
]
```

论文列表：
"""


def _build_interests_text(interests: list[str]) -> str:
    return "\n".join(f"   - {item}" for item in interests)


def _parse_json_response(raw: str) -> list[dict]:
    """从 LLM 回复中提取 JSON 数组。"""
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
    if json_match:
        raw = json_match.group(1)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raw = re.sub(r",\s*}", "}", raw)
        raw = re.sub(r",\s*]", "]", raw)
        return json.loads(raw)


def _backfill_scores(papers: list[Paper], score_map: dict[str, int]) -> None:
    """将 LLM 返回的评分回填到 Paper 对象。"""
    for p in papers:
        rid = p.arxiv_id.split("v")[0]
        for aid in score_map:
            if aid.startswith(rid) or rid.startswith(aid):
                p.relevance_score = score_map[aid]
                break


def screen_papers(client: Anthropic, model: str, papers: list[Paper],
                  interests: list[str] | None = None) -> list[Paper]:
    """标题初筛：用 LLM 对所有论文的标题快速打分，不生成摘要。"""
    if not papers:
        return papers

    if interests is None:
        interests = []

    items = []
    for i, p in enumerate(papers):
        items.append(
            f"### 论文 {i+1} | arxiv_id: {p.arxiv_id}\n"
            f"标题: {p.title}\n"
        )
    papers_text = "\n".join(items)

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SCREEN_PROMPT.format(interests=_build_interests_text(interests)),
        messages=[{"role": "user", "content": papers_text}],
        thinking={"type": "disabled"},
    )

    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        print(f"  LLM 未返回文本: {response.content}")
        return papers
    raw = text_blocks[0].text.strip()
    print(f"  LLM 响应前 200 字符: {raw[:200]}")
    results = _parse_json_response(raw)

    score_map = {r["arxiv_id"]: r.get("relevance_score", 5) for r in results}
    _backfill_scores(papers, score_map)
    return papers


def summarize(client: Anthropic, model: str, papers: list[Paper],
              interests: list[str] | None = None) -> list[Paper]:
    """批量调用 DeepSeek 生成详细摘要和评分。"""
    if not papers:
        return papers

    if interests is None:
        interests = []

    # 构建论文列表文本
    items = []
    for i, p in enumerate(papers):
        authors = ", ".join(p.authors[:5])
        if len(p.authors) > 5:
            authors += " et al."
        items.append(
            f"### 论文 {i+1} | arxiv_id: {p.arxiv_id}\n"
            f"标题: {p.title}\n"
            f"作者: {authors}\n"
            f"摘要: {p.abstract[:1200]}\n"
        )
    papers_text = "\n".join(items)

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=PROMPT.format(interests=_build_interests_text(interests)),
        messages=[{"role": "user", "content": papers_text}],
        thinking={"type": "disabled"},
    )

    text_blocks = [b for b in response.content if b.type == "text"]
    if not text_blocks:
        print(f"  LLM 未返回文本: {response.content}")
        return papers
    raw = text_blocks[0].text.strip()
    print(f"  LLM 响应前 200 字符: {raw[:200]}")
    results = _parse_json_response(raw)

    # 回填结果
    score_map = {}
    summary_map = {}
    for r in results:
        score_map[r["arxiv_id"]] = r.get("relevance_score", 5)
        summary_map[r["arxiv_id"]] = r.get("summary_cn", "")

    for p in papers:
        rid = p.arxiv_id.split("v")[0]
        for aid in score_map:
            if aid.startswith(rid) or rid.startswith(aid):
                p.relevance_score = score_map[aid]
                p.summary_cn = summary_map[aid]
                break

    return papers
