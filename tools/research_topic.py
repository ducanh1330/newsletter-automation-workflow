"""Research a newsletter topic using the Tavily Search API (free tier).

Usage:
    python tools/research_topic.py "<topic>" [--search-depth advanced] [--out PATH]

Writes a structured JSON file with Tavily's synthesized answer and the
underlying source results to .tmp/research_<slug>.json (or --out) and
prints the path.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

TAVILY_URL = "https://api.tavily.com/search"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "topic"


def research(topic: str, search_depth: str, max_results: int) -> dict:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        sys.exit("TAVILY_API_KEY is not set in .env")

    response = requests.post(
        TAVILY_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "query": topic,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": "advanced",
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()

    citations = [
        {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
        for r in payload.get("results", [])
    ]

    return {
        "topic": topic,
        "content": payload.get("answer", ""),
        "citations": citations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Research a topic via the Tavily Search API")
    parser.add_argument("topic", help="Newsletter topic / research question")
    parser.add_argument("--search-depth", default="advanced", choices=["basic", "advanced"])
    parser.add_argument("--max-results", type=int, default=8)
    parser.add_argument("--out", default=None, help="Output JSON path (default: .tmp/research_<slug>.json)")
    args = parser.parse_args()

    load_dotenv()

    result = research(args.topic, args.search_depth, args.max_results)

    out_path = Path(args.out) if args.out else Path(".tmp") / f"research_{slugify(args.topic)}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(str(out_path))


if __name__ == "__main__":
    main()
