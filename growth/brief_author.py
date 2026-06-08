"""LLM brief author — invents new tee design briefs from the perf report.

Replaces the human/agent creative step. Reads which designs are winning + the
current catalog (to avoid duplicates), asks Haiku for up to N complete briefs,
writes them to state/briefs.json. Each brief is the full downstream payload:
storefront fields + Recraft prompt + platform-fitted social copy.
"""
import json
import os
import sys

from growth.llm import complete_json

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state")
PERF = os.path.join(STATE, "perf-latest.json")
BRIEFS = os.path.join(STATE, "briefs.json")
PRODUCTS = os.environ.get("UNDERDOG_PRODUCTS", "")

BRAND = (
    "You are the creative director for Underdog Goods, a brand of original, "
    "funny-but-wholesome dog-lover t-shirts. Voice: warm, witty, plain-spoken. "
    "NEVER use em dashes. Designs are bold flat/retro VECTOR illustrations, "
    "centered, print-ready on a plain white background. Each design is one punchy "
    "concept a dog person would proudly wear. Audience: dog moms and dads, rescue "
    "people, homebodies, introverts."
)

SCHEMA_EXAMPLE = """Return ONLY a JSON array (no prose, no code fences) of design briefs.
Each element must have exactly these keys:
{
  "slug": "kebab-case-name-tee",
  "name": "Title Case Name Tee",
  "price_usd": 19.99,
  "headline": "one short hooky line for the product page",
  "blurb": "one warm sentence describing the vibe",
  "story": "2 to 3 sentences of brand story, no em dashes",
  "colors": ["Ash", "Dark Heather", "Light Blue"],
  "recraft_prompt": "detailed flat vector t-shirt graphic prompt ending with: centered, isolated on a plain white background, print-ready apparel graphic",
  "social": {
    "tt_hook": "scroll-stopping TikTok hook, max 70 chars, may include one emoji",
    "tt_tags": ["#dogsoftiktok", "#dogmom", "#..."],
    "pin_title": "SEO Pinterest title, max 100 chars",
    "pin_keywords": "comma, separated, search, keywords",
    "audience": "short phrase naming who this is for"
  }
}"""


def _existing_slugs():
    if PRODUCTS and os.path.exists(PRODUCTS):
        d = json.load(open(PRODUCTS))
        items = d if isinstance(d, list) else d.get("products", [])
        return [p["slug"] for p in items]
    return []


def author(n):
    perf = json.load(open(PERF)) if os.path.exists(PERF) else {}
    existing = _existing_slugs()
    winners = [k for k, v in (perf.get("designs") or {}).items() if (v or {}).get("score", 0) > 0]

    user = (
        f"The catalog already has these slugs, do NOT duplicate them or their themes too closely: {existing}\n"
        f"Designs showing real demand so far: {winners or 'none yet, this is a cold start'}\n\n"
        f"Invent {n} NEW dog-lover tee design(s). Lean mostly toward fresh variations on the "
        f"winning themes when there are winners, but always include at least one genuinely new angle. "
        f"Each slug must end in '-tee'.\n\n"
        + SCHEMA_EXAMPLE
    )

    briefs = complete_json(BRAND, user, max_tokens=2200)
    if isinstance(briefs, dict):
        briefs = briefs.get("briefs") or briefs.get("designs") or [briefs]
    out = [b for b in briefs if isinstance(b, dict) and b.get("slug") and b["slug"] not in existing][:n]
    os.makedirs(STATE, exist_ok=True)
    json.dump(out, open(BRIEFS, "w"), indent=2)
    return out


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    result = author(count)
    print(f"{len(result)} brief(s) -> {BRIEFS}")
    for b in result:
        print("  ", b["slug"], "|", b.get("social", {}).get("tt_hook", ""))
