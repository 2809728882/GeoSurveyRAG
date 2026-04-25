from __future__ import annotations

import argparse
import json
from pathlib import Path

from geosurvey_rag.rag import RagPipeline


def evaluate(eval_path: Path, top_k: int = 4) -> dict:
    pipeline = RagPipeline()
    cases = json.loads(eval_path.read_text(encoding="utf-8"))
    results = []
    hits = 0
    total_terms = 0
    matched_total = 0

    for case in cases:
        answer, sources = pipeline.answer(case["question"], top_k=top_k)
        source_text = "\n".join(source.text for source in sources)
        expected_terms = case.get("expected_terms", [])
        matched_terms = [term for term in expected_terms if term in answer or term in source_text]
        total_terms += len(expected_terms)
        matched_total += len(matched_terms)
        if matched_terms:
            hits += 1
        results.append(
            {
                "question": case["question"],
                "expected_terms": expected_terms,
                "matched_terms": matched_terms,
                "term_coverage": round(len(matched_terms) / len(expected_terms), 4)
                if expected_terms
                else 0,
                "source_count": len(sources),
                "top_sources": [source.source for source in sources],
            }
        )

    return {
        "case_count": len(cases),
        "hit_rate": round(hits / len(cases), 4) if cases else 0,
        "term_coverage": round(matched_total / total_terms, 4) if total_terms else 0,
        "results": results,
    }


def write_markdown_report(result: dict, report_path: Path) -> None:
    lines = [
        "# GeoSurveyRAG 离线评测报告",
        "",
        f"- 问题数量：{result['case_count']}",
        f"- 命中率：{result['hit_rate']}",
        f"- 关键词覆盖率：{result['term_coverage']}",
        "",
        "| # | 问题 | 覆盖率 | 命中关键词 |",
        "|---|---|---:|---|",
    ]
    for index, item in enumerate(result["results"], start=1):
        matched = "、".join(item["matched_terms"]) or "无"
        question = item["question"].replace("|", " ")
        lines.append(f"| {index} | {question} | {item['term_coverage']} | {matched} |")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run offline retrieval evaluation.")
    parser.add_argument("--eval", type=Path, default=Path("eval/golden_questions.json"))
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()
    result = evaluate(args.eval, args.top_k)
    if args.report:
        write_markdown_report(result, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
