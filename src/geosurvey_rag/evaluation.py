from __future__ import annotations

import argparse
import json
from pathlib import Path

from geosurvey_rag.llm import LocalLLM
from geosurvey_rag.rag import RagPipeline
from geosurvey_rag.settings import settings


def evaluate(eval_path: Path, top_k: int = 4, index_dir: Path | str = settings.index_dir) -> dict:
    pipeline = RagPipeline(index_dir)
    # Evaluation is reproducible, offline and never bills an external LLM API.
    pipeline.llm = LocalLLM()
    cases = json.loads(eval_path.read_text(encoding="utf-8"))
    results = []
    source_hits = keyword_hits = 0
    rank_total = 0.0
    source_case_count = total_terms = source_matched_total = answer_matched_total = 0
    negative_count = negative_passed = 0
    for case in cases:
        answer, sources = pipeline.answer(case["question"], top_k=top_k)
        source_text = "\n".join(source.text for source in sources)
        expected_terms = case.get("expected_terms", [])
        source_terms = [term for term in expected_terms if term in source_text]
        answer_terms = [
            term for term in expected_terms if term in answer.replace(case["question"], "")
        ]
        total_terms += len(expected_terms)
        source_matched_total += len(source_terms)
        answer_matched_total += len(answer_terms)
        keyword_hits += bool(source_terms)
        expected_sources = case.get("expected_sources", [])
        ranks = [
            rank
            for rank, source in enumerate(sources, 1)
            if Path(source.source).name in expected_sources
        ]
        rank = min(ranks) if ranks else None
        if expected_sources:
            source_case_count += 1
            source_hits += rank is not None
            rank_total += 1 / rank if rank else 0
        if case.get("expect_no_evidence"):
            negative_count += 1
            negative_passed += not sources
        coverage = len(source_terms) / len(expected_terms) if expected_terms else 0.0
        results.append(
            {
                "question": case["question"],
                "expected_terms": expected_terms,
                "matched_terms": source_terms,
                "term_coverage": round(coverage, 4),
                "answer_term_coverage": round(len(answer_terms) / len(expected_terms), 4)
                if expected_terms
                else 0,
                "expected_sources": expected_sources,
                "first_relevant_rank": rank,
                "source_count": len(sources),
                "top_sources": [s.source for s in sources],
                "expect_no_evidence": case.get("expect_no_evidence", False),
            }
        )
    return {
        "case_count": len(cases),
        "top_k": top_k,
        "retrieval_method": settings.retrieval_mode,
        "answer_mode": "offline_extract",
        "source_case_count": source_case_count,
        "source_hit_rate": round(source_hits / source_case_count, 4) if source_case_count else 0,
        "mrr": round(rank_total / source_case_count, 4) if source_case_count else 0,
        "hit_rate": round(keyword_hits / len(cases), 4) if cases else 0,
        "term_coverage": round(source_matched_total / total_terms, 4) if total_terms else 0,
        "answer_term_coverage": round(answer_matched_total / total_terms, 4) if total_terms else 0,
        "negative_case_count": negative_count,
        "no_evidence_rate": round(negative_passed / negative_count, 4) if negative_count else 0,
        "results": results,
    }


def write_markdown_report(result: dict, report_path: Path) -> None:
    lines = [
        "# GeoSurveyRAG 离线评测报告",
        "",
        f"- 样本数：{result['case_count']}（相关来源标注 {result['source_case_count']}；无证据样本 {result['negative_case_count']}）",
        f"- 检索方式：{result['retrieval_method']}；TopK：{result['top_k']}；回答方式：离线摘录",
        f"- 标注来源命中率 Hit@K：{result['source_hit_rate']}；MRR：{result['mrr']}",
        f"- 检索片段关键词覆盖率：{result['term_coverage']}",
        f"- 回答关键词覆盖率：{result['answer_term_coverage']}",
        f"- 无证据样本空召回率：{result['no_evidence_rate']}",
        "",
        "以上指标仅针对随仓库提供的演示知识库和人工编写样本，不代表生产准确率、事实正确率或大模型忠实度。",
        "关键词覆盖率独立统计检索片段和离线摘录，不再将两者混合计算。排序分数也不是置信概率。",
        "",
        "| # | 问题 | 来源首命中排名 | 来源关键词覆盖率 | 回答关键词覆盖率 |",
        "|---|---|---:|---:|---:|",
    ]
    for index, item in enumerate(result["results"], 1):
        question = item["question"].replace("|", " ")
        rank = item["first_relevant_rank"] or "—"
        lines.append(
            f"| {index} | {question} | {rank} | {item['term_coverage']} | {item['answer_term_coverage']} |"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run offline source retrieval and excerpt evaluation."
    )
    parser.add_argument("--eval", type=Path, default=Path("eval/golden_questions.json"))
    parser.add_argument("--index", type=Path, default=settings.index_dir)
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be positive")
    result = evaluate(args.eval, args.top_k, args.index)
    if args.report:
        write_markdown_report(result, args.report)
    serialized = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
