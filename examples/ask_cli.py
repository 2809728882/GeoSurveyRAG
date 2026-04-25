from __future__ import annotations

import argparse

from geosurvey_rag.agent import GeoAgent, format_tool_summary
from geosurvey_rag.rag import RagPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask GeoSurveyRAG from command line.")
    parser.add_argument("question")
    args = parser.parse_args()

    agent = GeoAgent()
    tool_calls = agent.maybe_run_tools(args.question)
    answer, sources = RagPipeline().answer(args.question, tool_summary=format_tool_summary(tool_calls))
    print(answer)
    print("\nSources:")
    for source in sources:
        print(f"- {source.source} score={source.score}")


if __name__ == "__main__":
    main()
