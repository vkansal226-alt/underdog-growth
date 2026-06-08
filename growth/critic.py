"""LLM vision critic — the brand-safety gate.

Looks at the actual rendered tee mockup and scores it. Anything below the
threshold is rejected so it never reaches the live accounts. This replaces the
human review step.
"""
import json
import os
import sys

from growth.llm import complete_json

THRESHOLD = int(os.environ.get("CRITIC_THRESHOLD", "70"))

RUBRIC = (
    "You are a brand art director for Underdog Goods (funny-but-wholesome dog-lover "
    "t-shirts). You are shown a t-shirt MOCKUP image. Score it 0-100 overall, judging: "
    "(1) brand fit (warm, witty, dog-themed, not generic), (2) humor / shirt appeal, "
    "(3) text legibility and print quality (no garbled or misspelled words, no artifacts), "
    "(4) originality. Reject anything off-brand, ugly, broken, low-effort, or with "
    "unreadable/garbled text. Return ONLY JSON: "
    '{"score": <0-100 int>, "pass": <true|false>, "reasons": "<one short sentence>"}'
    f". Set pass=true only if score >= {THRESHOLD}."
)


def review(mockup_path):
    png = open(mockup_path, "rb").read()
    v = complete_json("Return only JSON, no prose.", RUBRIC, image_png=png, max_tokens=400)
    score = int(v.get("score", 0))
    v["score"] = score
    v["pass"] = bool(v.get("pass")) and score >= THRESHOLD
    return v


if __name__ == "__main__":
    print(json.dumps(review(sys.argv[1]), indent=2))
