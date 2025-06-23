"""
SEO Analyzer Core Logic
– Fetch page        (fetch_html)
– Parse with BS4    (BeautifulSoup)
– Run 12 on-page checks
– Return a single report dict
"""

from collections import Counter
import re, requests, urllib.parse, time
import tldextract, textstat, spacy
from bs4 import BeautifulSoup

# ----------------- models & headers ---------------- #
HEADERS = {"User-Agent": "Mozilla/5.0 (SEO Analyzer)"}

try:
    NLP = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    NLP = spacy.load("en_core_web_sm")

# ----------------- optional: language detection ----- #
try:
    from langdetect import detect
except ImportError:
    detect = lambda text: "en"  # fallback to English

# ----------------- helper: download HTML ----------- #
def fetch_html(url: str, timeout: int = 10) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        raise RuntimeError(f"Failed to fetch HTML from {url}: {e}")

# ----------------- individual checks --------------- #
def check_readability(soup):
    text = soup.get_text(" ", strip=True)
    score = textstat.flesch_reading_ease(text)
    normalized_score = max(min(score, 100), 0)
    suggestion = None
    if normalized_score < 60:
        suggestion = "Reading Ease below 60; shorten sentences and use simpler words."
    return {"score": round(normalized_score, 1), "suggest": suggestion}

def check_viewport(soup):
    tag = soup.find("meta", attrs={"name": "viewport"})
    present = bool(tag)
    score = 100 if present else 0
    suggestion = None if present else "Add <meta name='viewport'> for mobile responsiveness."
    return {"score": score, "suggest": suggestion}

def check_title(soup):
    tag = soup.title.string.strip() if soup.title and soup.title.string else ""
    ln = len(tag)
    sug = (
        "Add a descriptive <title> (50-60 chars)." if ln == 0 else
        "Make the title more descriptive."        if ln < 30 else
        "Shorten the title to ≤ 60 chars."        if ln > 65 else
        None
    )
    return {"value": tag, "length": ln, "suggest": sug}

def check_meta_description(soup):
    meta = soup.find("meta", attrs={"name": "description"})
    txt  = meta.get("content", "").strip() if meta else ""
    ln   = len(txt)
    sug  = (
        "Add a meta description (120-155 chars)." if ln == 0 else
        "Meta description too short."            if ln < 70 else
        "Meta description too long."             if ln > 160 else
        None
    )
    return {"value": txt, "length": ln, "suggest": sug}

def check_h1(soup):
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    sug = (
        "No <h1> tag found."            if len(h1s) == 0 else
        "Multiple <h1> tags detected."  if len(h1s) > 1 else
        None
    )
    return {"values": h1s, "count": len(h1s), "suggest": sug}

def check_image_alts(soup):
    imgs     = soup.find_all("img")
    missing  = [img.get("src") for img in imgs if not img.get("alt")]
    sug = f"{len(missing)} of {len(imgs)} images lack alt text." if missing else None
    return {"total": len(imgs), "missing": missing[:10], "suggest": sug}

def check_links(soup, base_url):
    links   = soup.find_all("a", href=True)
    base    = tldextract.extract(base_url).domain
    external = sum(
        1 for a in links
        if (href := a["href"]) and not href.startswith(("#", "mailto:")) and
           tldextract.extract(href).domain not in ("", base)
    )
    return {"total": len(links), "external": external}

def extract_keywords(soup, topn=15):
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True).lower())
    if detect(text) != "en":
        return [{"word": "Non-English page", "count": 0}]
    
    words = [
        t.lemma_ for t in NLP(text)
        if t.pos_ in ("NOUN", "PROPN", "ADJ") and not t.is_stop and t.is_alpha and len(t) > 2
    ]
    sorted_words = sorted(Counter(words).items(), key=lambda p: p[1], reverse=True)[:topn]
    return [{"word": w, "count": c} for w, c in sorted_words]

def check_schema(soup):
    present = bool(soup.find_all("script", type="application/ld+json"))
    sug     = None if present else "No JSON-LD structured data detected."
    return {"present": present, "suggest": sug}

def check_canonical(soup, url):
    link = soup.find("link", rel="canonical")
    href = link["href"] if link and link.has_attr("href") else ""
    same = urllib.parse.urljoin(url, "/") == urllib.parse.urljoin(href or "", "/")
    sug  = (
        "No canonical tag found."            if not link else
        f"Canonical ({href}) doesn’t match this page." if not same else
        None
    )
    return {"href": href, "suggest": sug}

def check_robots_sitemap(url):
    base   = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    try:
        txt    = requests.get(base + "/robots.txt", timeout=5).text.lower() if base else ""
    except Exception:
        txt = ""
    robots = bool(txt)
    site   = "sitemap:" in txt
    sug = (
        "robots.txt missing."                 if not robots else
        "robots.txt lacks Sitemap directive." if robots and not site else
        None
    )
    return {"robots": robots, "sitemap": site, "suggest": sug}

def check_social_meta(soup):
    missing = [name for name, sel in {
        "og:title":  ("meta", {"property": "og:title"}),
        "og:desc":   ("meta", {"property": "og:description"}),
        "og:image":  ("meta", {"property": "og:image"}),
        "twitter:card": ("meta", {"name": "twitter:card"})
    }.items() if not soup.find(*sel)]
    sug = f"Missing social tags: {', '.join(missing)}." if missing else None
    return {"missing": missing, "suggest": sug}

def check_heading_hierarchy(soup):
    levels = [int(h.name[1]) for h in soup.find_all(re.compile(r'^h[1-6]$'))]
    bad    = any(b - a > 1 for a, b in zip(levels, levels[1:]))
    sug    = "Heading levels skip; fix hierarchy." if bad else None
    return {"levels": levels, "suggest": sug}

# ----------------- master analyzer ---------------- #

def prepare_chart_data(report):
    # 1) Base chart: Scores from checks that have 'score' keys
    labels = []
    scores = []
    suggestions = []
    for key, val in report.items():
        if isinstance(val, dict) and "score" in val:
            labels.append(key.replace("_", " ").title())
            scores.append(val["score"])
            suggestions.append(val.get("suggest"))

    base_chart_data = {
        "labels": labels,
        "scores": scores,
        "suggestions": suggestions
    }

    # 2) Keyword density bar chart (top 10 keywords)
    keyword_density = {
        "labels": [kw["word"] for kw in report.get("keywords", [])],
        "values": [kw["count"] for kw in report.get("keywords", [])]
    }

    # 3) External vs internal links pie chart
    total_links = report.get("links", {}).get("total", 0)
    external_links = report.get("links", {}).get("external", 0)
    internal_links = max(total_links - external_links, 0)
    links_pie = {
        "labels": ["Internal Links", "External Links"],
        "values": [internal_links, external_links]
    }

    # 4) Image alt text coverage doughnut chart
    total_images = report.get("images", {}).get("total", 0)
    missing_alt = len(report.get("images", {}).get("missing", []))
    images_alt_coverage = {
        "labels": ["Images with Alt", "Images Missing Alt"],
        "values": [total_images - missing_alt, missing_alt]
    }

    # 5) Mobile usability issues bar chart (example fixed values)
    mobile_issues = {
        "labels": ["Font Size", "Tap Targets", "Viewport"],
        "values": [3, 1, 2]
    }

    # 6) Readability by page sections (example fixed values)
    readability_sections = {
        "labels": ["Intro", "Body", "Conclusion"],
        "values": [60, 55, 70]
    }

    # 7) Page load speed gauge chart
    load_speed = {
        "value": report.get("page_load_time", 3.2),
        "max": 10
    }

    # Return all charts in one dictionary
    return {
        **base_chart_data,
        "keyword_density": keyword_density,
        "links_distribution": links_pie,
        "image_alt_coverage": images_alt_coverage,
        "mobile_issues": mobile_issues,
        "readability_sections": readability_sections,
        "page_load_speed": load_speed
    }


def analyze_url(url):
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else ''
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'].strip() if description else ''

        # Other parsing logic...

        return {
            "url": url,
            "title": title,  # ✅ Add this line
            "title_len": len(title),
            "desc_len": len(description),
            # more keys...
        }

    except Exception as e:
        return {
            "url": url,
            "title": "",  # ✅ Also add here for consistency
            "title_len": 0,
            "desc_len": 0,
            # more default keys...
            "error": str(e)
        }


# ----------------- CLI for Testing ---------------- #
if __name__ == "__main__":
    import json
    test_url = "https://www.example.com"
    try:
        report = analyze_url(test_url)
        print(json.dumps(report, indent=2))
    except Exception as e:
        print(f"Error: {e}")