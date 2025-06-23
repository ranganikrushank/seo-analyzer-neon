"""
Very simple heuristic: each issue deducts points.
Tweak weights/thresholds as you like.
"""
from analyzer import (
    check_title,
    check_meta_description,
    check_h1,
    check_image_alts,
    check_schema,
)

# weights for each section (0-100 total)
WEIGHTS = {
    "title": 20,
    "meta_desc": 15,
    "h1": 10,
    "images": 10,
    "schema": 5,
    # remaining 40 pts reserved for future checks (page speed, mobile, etc.)
}


def score_report(report: dict) -> int:
    score = 100
    if report["title"]["suggest"]:
        score -= WEIGHTS["title"]
    if report["meta_desc"]["suggest"]:
        score -= WEIGHTS["meta_desc"]
    if report["h1"]["suggest"]:
        score -= WEIGHTS["h1"]
    if report["images"]["suggest"]:
        score -= WEIGHTS["images"]
    if report["schema"]["suggest"]:
        score -= WEIGHTS["schema"]

    # floor/ceiling
    return max(0, min(100, score))