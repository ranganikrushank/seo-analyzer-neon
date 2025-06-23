# 🔍 SEO AI Analyzer

A one-page Flask web app that lets anyone paste a URL and instantly receive a rich, chart-filled SEO audit:

| ![Demo screenshot](docs/demo.png) |
|----------------------------------|

* **On-page checks** – title/description length, headings, alt text coverage, schema, canonical, robots, social meta, readability and more.  
* **Charts everywhere** – Chart.js visualisations for scores, keyword density, backlinks, mobile issues, readability, load speed and an improvement radar.  
* **Website preview** – live screenshot pulled from [thum.io](https://thum.io) so users recognise the site at a glance.  
* **Historical trend** – simulated SEO score‐trend line (wire up to a DB if you want real history).  
* **Instant PDF** – “Download PDF” button renders a lightweight report via ReportLab (no wkhtmltopdf dependency).  
* **Gamified bump** – every time the same token revisits the tool we show a small “score increase” (+1–5 %).  
* **Zero DB by default** – everything lives in memory; drop in Redis/Postgres if you need persistence.  
* **Tailwind-powered** responsive UI – looks great on laptop & mobile out of the box.  

---

## ✨ Live demo

> If you have the app hosted, drop the link here – e.g.
> **https://seo-ai-analyzer.onrender.com**

---

## 🏗️  Project structure

├── app.py ← main Flask entry-point
├── analyzer.py ← SEO scraping & scoring logic
├── scoring.py ← single 0-100 aggregate scorer
├── requirements.txt ← Python deps
├── static/
│ ├── style.css ← (optional) additional styling
│ └── favicon.ico
├── templates/
│ ├── base.html ← global layout + Tailwind import
│ ├── index.html ← landing page (URL form)
│ └── result.html ← full report page
└── README.md




---

## 🚀  Quick-start

```bash
git clone https://github.com/<ranganikrushank>/seo-ai-analyzer.git
cd seo-ai-analyzer

# 1 – create & activate a virtualenv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2 – install Python dependencies
pip install -r requirements.txt

# 3 – run the dev server
python app.py
# open http://127.0.0.1:5000 in your browser