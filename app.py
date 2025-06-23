import psycopg2
import os
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file, jsonify, make_response, session
)
from io import BytesIO
from flask_cors import CORS
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from werkzeug.security import generate_password_hash, check_password_hash

from analyzer import analyze_url, prepare_chart_data
from scoring import score_report


import os
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)



app = Flask(__name__)
app.secret_key = "lwsdTtVN89RHQHrn1q2Yz4Ic3TYapQMaIhPVH55F0DM"
CORS(app)

DB_PATH = "seo_analyzer.db"


def save_analysis_to_db(user_id, url, seo_score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO url_analysis (user_id, url, seo_score)
        VALUES (%s, %s, %s)
    """, (user_id, url, seo_score))
    conn.commit()
    conn.close()


# -------------- Auth --------------------


from functools import wraps
from flask import make_response

def nocache(view):
    @wraps(view)
    def no_cache_view(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache_view






@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)", (username, email, password))
            conn.commit()
        except psycopg2.IntegrityError:
            flash("Email already registered.", "error")
            return redirect("/register")
        conn.close()
        flash("Registration successful! Please login.", "success")
        return redirect("/login")
    return render_template("register.html")

# @app.route("/premium_features", methods=["GET", "POST"])
# def premium_features():
#     features = [
#         {"title": "🕵️ Advanced Link Quality Audit", "description": "Broken links, nofollow/dofollow, anchor text analysis."},
#         {"title": "📥 Download Branded PDF Reports", "description": "Professional summary of the entire audit."},
#         {"title": "💬 Priority Support / Chatbot Help", "description": "Get priority answers from the built-in assistant."},
#         {"title": "📊 Interactive Google Charts Dashboard", "description": "Beautiful, animated visualizations of your audit."},
#         {"title": "📱 Full Mobile Optimization Audit", "description": "Deep dive into tap targets, layout, responsiveness."},
#         {"title": "🔍 Competitor SEO Comparison", "description": "Compare your SEO with competitors' URLs."},
#         {"title": "⚡ Speed Insights Breakdown", "description": "Optimize scripts, images, and resources."},
#         {"title": "📋 Content Readability & AI Suggestions", "description": "Improve your content with AI-powered suggestions."},
#         {"title": "💬 AI SEO Assistant (Chatbot)", "description": "Ask anything about your SEO performance."},
#         {"title": "📊 Export to Excel or CSV", "description": "Download all reports in CSV or XLS."},
#         {"title": "🔁 Saved History of Past Analyses", "description": "Track your improvements over time."},
#     ]
#     return render_template("premium_features.html", features=features)

@app.route('/premium-features')
def premium_features():
    return render_template('premium_features.html')



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password, plan FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["plan"] = user[3]

            # 🔁 Redirect based on plan
            if user[3] == "premium":
                return redirect("/dashboard_premium")
            else:
                return redirect("/dashboard")

        # flash("Invalid credentials.", "error")
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect("/login")



app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = False  # True if using HTTPS
app.config["SESSION_PERMANENT"] = False



# -------------- Core Routes --------------------

@app.route("/", methods=["GET"])
def home():
    return redirect("/login")


@app.route("/dashboard", methods=["GET", "POST"])
@nocache
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    # Refresh user plan from DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plan FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["plan"] = user[0]

    # Redirect premium users
    if session["plan"] == "premium":
        return redirect("/dashboard_premium")

    # Handle Analyze button for free users → show promo page
    if request.method == "POST":
        return redirect("/free-info")

    return render_template("index.html")


@app.route("/free-info")
def free_info():
    return render_template("free_version.html")



@app.route("/contact", methods=["POST"])
def contact():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    # Store it in a file or DB — here we append to a simple file
    with open("contact_requests.txt", "a", encoding="utf-8") as f:
        f.write(f"Name: {name}\nEmail: {email}\nMessage: {message}\n---\n")

    flash("✅ Your message has been recieved. I'll contact you soon!", "success")
    return redirect("/free-info")





@app.route("/upgrade", methods=["GET", "POST"])
def upgrade():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        # Save the payment request to DB
        upi_id = request.form["upi_id"]
        amount = request.form["amount"]
        message = request.form["message"]
        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO payment_requests (user_id, upi_id, amount, message)
            VALUES (%s, %s, %s, %s)
        """, (user_id, upi_id, amount, message))
        conn.commit()
        conn.close()

        flash("Payment request submitted. We'll verify and upgrade you shortly.", "success")
        return redirect("/")
    
    return render_template("upgrade.html")

@app.route("/dashboard_premium")
@nocache
def dashboard_premium():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("plan") != "premium":
        flash("This page is for premium users only.")
        return redirect("/premium_features")
    return render_template("dashboard_premium.html")

@app.before_request
def require_login_for_protected_pages():
    protected_paths = [
        "/dashboard", "/dashboard_premium",
        "/premium", "/premium/link-audit", "/premium/charts",
        "/premium/speed-insights", "/premium/seo-chatbot",
        "/premium/mobile-audit", "/premium/competitor"
    ]
    if any(request.path.startswith(path) for path in protected_paths):
        if "user_id" not in session:
            return redirect("/login")



@app.route("/verify_payments", methods=["GET", "POST"])
def verify_payments():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        request_id = request.form["request_id"]
        action = request.form["action"]

        # Get user_id from request
        cursor.execute("SELECT user_id FROM payment_requests WHERE id = %s", (request_id,))
        user = cursor.fetchone()
        if user:
            user_id = user[0]
            if action == "approve":
                cursor.execute("UPDATE users SET plan = 'premium' WHERE id = %s", (user_id,))
                cursor.execute("UPDATE payment_requests SET status = 'approved' WHERE id = %s", (request_id,))
            elif action == "reject":
                cursor.execute("UPDATE payment_requests SET status = 'rejected' WHERE id = %s", (request_id,))
            conn.commit()

    cursor.execute("""
        SELECT pr.id, u.username, pr.upi_id, pr.amount, pr.message, pr.status, pr.created_at
        FROM payment_requests pr
        JOIN users u ON pr.user_id = u.id
        ORDER BY pr.created_at DESC
    """)
    requests = cursor.fetchall()
    conn.close()

    return render_template("verify_payments.html", requests=requests)





@app.route("/analyze", methods=["POST"])
def analyze():
    if "user_id" not in session:
        return jsonify({"error": "Login required."}), 401

    if session.get("plan") != "premium":
        return jsonify({"error": "This feature is available for premium users only. Please upgrade."}), 403


    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({"error": "Missing URL."}), 400

        url = data['url']
        report = analyze_url(url)
        score = score_report(report)
        save_analysis_to_db(session["user_id"], url, score)

        return jsonify({"score": score, "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    
    


@app.route("/result")
def result():
    url = "https://example.com"
    score = 75
    report = {
        "keywords": [
            {"word": "SEO", "count": 10},
            {"word": "AI", "count": 8}
        ],
    }
    chart_data = {
        "keyword_density": {"labels": ["SEO", "AI"], "values": [10, 8]},
        "links_distribution": {"labels": ["Good", "Bad"], "values": [5, 2]},
        "mobile_issues": {"labels": ["Issue1", "Issue2"], "values": [3, 1]},
        "readability_sections": {"labels": ["Intro", "Body"], "values": [80, 70]},
        "page_load_speed": {"value": 60, "max": 100},
    }

    screenshot_url = f"https://image.thum.io/get/{url}"

    return render_template(
        "result.html",
        url=url,
        score=score,
        report=report,
        chart_data=chart_data,
        screenshot_url=screenshot_url,
        pdf_mode=False,
        zip=zip
    )


@app.route("/pdf_report")
def pdf_report():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("plan") != "premium":
        flash("Premium only. Please upgrade to download PDF reports.")
        return redirect("/upgrade")

    target_url = request.args.get("target")
    if not target_url:
        flash("Missing URL for PDF export.", "error")
        return redirect(url_for("index"))

    report = analyze_url(target_url)
    score = score_report(report)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"SEO Report for {target_url}")
    p.setFont("Helvetica", 12)
    p.drawString(50, height - 80, f"Overall Score: {score}")

    y = height - 120
    p.drawString(50, y, "Keywords:")
    y -= 20
    for kw in report.get("keywords", []):
        p.drawString(60, y, f"{kw['word']}: {kw['count']}")
        y -= 15
        if y < 50:
            p.showPage()
            y = height - 50

    p.showPage()
    p.save()

    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=seo_report.pdf"
    return response

from flask import render_template, request, session, redirect, flash
from link_audit import fetch_html, audit_links, save_audit_to_db

@app.route("/premium/link-audit", methods=["GET", "POST"])
def premium_link_audit():
    if "user_id" not in session or session.get("plan") != "premium":
        flash("Please upgrade to premium to access this feature.", "warning")
        return redirect("/upgrade")

    if request.method == "POST":
        url = request.form.get("url", "").strip()  # ✅ use .get() with default fallback

        if not url:
            flash("Please enter a valid URL.", "danger")
            return redirect("/premium/link-audit")

        html = fetch_html(url)
        if not html:
            flash("Failed to fetch the website content.", "danger")
            return redirect("/premium/link-audit")

        audit_data = audit_links(html, url)
        save_audit_to_db(session["user_id"], url, audit_data)
        return render_template("link_audit_result.html", audit_data=audit_data, target_url=url)

    return render_template("link_audit.html")



@app.route("/premium/charts", methods=["GET", "POST"])
def premium_charts():
    if "user_id" not in session or session.get("plan") != "premium":
        flash("Only premium users can access interactive charts.", "error")
        return redirect("/upgrade")

    chart_data = None
    target_url = None

    if request.method == "POST":
        target_url = request.form.get("url", "").strip()
        if not (target_url.startswith("http://") or target_url.startswith("https://")):
            flash("Please enter a valid URL with http:// or https://", "error")
            return redirect("/premium/charts")

        try:
            from analyzer import analyze_url, prepare_chart_data
            report = analyze_url(target_url)
            raw_data = prepare_chart_data(report)

            # ✅ Zip label-value pairs in Python
            chart_data = {
                "keyword_density": [("Keyword1", 5), ("Keyword2", 3)],
                "links_distribution": [("Internal", 12), ("External", 6)],
                "mobile_issues": [("Viewport", 1), ("Font Size", 2)],
                "readability_sections": [("Intro", 70), ("Body", 60)],
                "image_alt_coverage": [("With Alt", 10), ("Without Alt", 3)],
                "page_load_speed": {"value": 7.5},
                "meta_tags": [("Meta Description", 1), ("Title Tag", 1)],
                "headings": [("H1", 1), ("H2", 4), ("H3", 3)],
                "word_count": [("Header", 50), ("Body", 600)],
                "internal_external_links": [("Internal", 10), ("External", 5)],
                "https_usage": [("HTTPS", 12), ("HTTP", 1)],
                "canonical_tags": [("Present", 1), ("Missing", 0)]
            }



        except Exception as e:
            flash(f"Error analyzing URL: {e}", "error")

    return render_template("interactive_charts.html", chart_data=chart_data, target_url=target_url)





import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def calculate_speed_score(soup, url):
    score = 0

    # Viewport tag
    if soup.find('meta', attrs={'name': 'viewport'}):
        score += 2

    # Minified CSS/JS detection
    scripts = soup.find_all('script', src=True)
    stylesheets = soup.find_all('link', rel='stylesheet')

    minified_js = sum(1 for s in scripts if '.min.js' in s['src'])
    minified_css = sum(1 for s in stylesheets if '.min.css' in s.get('href', ''))

    if minified_js > 0:
        score += 1
    if minified_css > 0:
        score += 1

    # Uses CDN (check script or CSS links with known CDNs)
    cdn_hosts = ['cdn.', 'cloudflare', 'bootstrapcdn', 'googleapis']
    all_links = [s['src'] for s in scripts if 'src' in s.attrs] + [l['href'] for l in stylesheets if 'href' in l.attrs]
    if any(any(host in link for host in cdn_hosts) for link in all_links):
        score += 2

    # Image tags with dimensions
    imgs = soup.find_all('img')
    has_size = sum(1 for img in imgs if img.get('width') and img.get('height'))
    if has_size / len(imgs) > 0.5 if imgs else False:
        score += 1

    # Number of CSS/JS files
    if len(stylesheets) < 10:
        score += 1
    if len(scripts) < 10:
        score += 1

    # Avoid outdated tags
    if not soup.find(['marquee', 'blink']):
        score += 1

    return min(score, 10)

@app.route('/premium/mobile-audit', methods=['GET', 'POST'])
def mobile_audit():
    results = None
    url = None

    if request.method == 'POST':
        url = request.form.get('url')
        try:
            res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(res.text, 'html.parser')

            viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
            responsive = bool(viewport_tag)
            tap_target_issues = "button, a".join([tag.name for tag in soup.find_all(['button', 'a']) if tag.get('style') and 'padding' not in tag['style']])
            font_small = any(int(tag.get('size', '12')) < 14 for tag in soup.find_all('font'))

            score = calculate_speed_score(soup, url)

            results = {
                "responsive": responsive,
                "viewport": viewport_tag is not None,
                "tap_targets": tap_target_issues == "",
                "font_size": not font_small,
                "mobile_speed": round(score, 1)
            }
        except Exception as e:
            flash(f"Error fetching URL: {e}", "danger")

    return render_template("mobile_audit.html", results=results, url=url)







def analyze_url(url):
    try:
        res = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else ''
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'].strip() if description else ''

        headings = {f'h{i}': len(soup.find_all(f'h{i}')) for i in range(1, 7)}

        links = soup.find_all('a', href=True)
        internal_links = [a['href'] for a in links if url in a['href']]
        external_links = [a['href'] for a in links if url not in a['href']]

        body_text = soup.get_text(separator=' ', strip=True)
        word_count = len(body_text.split())

        speed_score = 5 + (1 if soup.find('meta', attrs={'name': 'viewport'}) else 0)

        # SEO Score (simple formula — you can improve it)
        seo_score = min(100, (
            len(title) * 0.2 +
            len(description) * 0.1 +
            word_count * 0.05 +
            len(internal_links) * 1 +
            speed_score * 2
        ))

        return {
            'url': url,
            'title_len': len(title),
            'desc_len': len(description),
            'word_count': word_count,
            'headings': headings,
            'internal_links': len(internal_links),
            'external_links': len(external_links),
            'speed_score': speed_score,
            'seo_score': round(seo_score)
        }

    except Exception as e:
        return {
            'url': url,
            'title_len': 0,
            'desc_len': 0,
            'word_count': 0,
            'headings': {f'h{i}': 0 for i in range(1, 7)},
            'internal_links': 0,
            'external_links': 0,
            'speed_score': 0,
            'seo_score': 0,
            'error': str(e)
        }

@app.route('/premium/compare-competitor', methods=['GET', 'POST'])
def competitor_comparison():
    results = []
    if request.method == 'POST':
        urls = request.form.getlist('urls')
        for url in urls:
            if url.strip():
                results.append(analyze_url(url.strip()))
    return render_template('competitor_comparison.html', results=results)


from flask import request, send_file
import pandas as pd
from io import BytesIO

@app.route('/export_competitor_report/<filetype>', methods=['POST'])
def export_competitor_report(filetype):
    urls = request.form.getlist('urls')
    results = [analyze_url(url.strip()) for url in urls if url.strip()]

    if not results:
        return "No data to export."

    # Create DataFrame
    data = {
        'URL': [r['url'] for r in results],
        'SEO Score': [r['seo_score'] for r in results],
        'Title Length': [r['title_len'] for r in results],
        'Description Length': [r['desc_len'] for r in results],
        'Word Count': [r['word_count'] for r in results],
        'Internal Links': [r['internal_links'] for r in results],
        'External Links': [r['external_links'] for r in results],
        'Speed Score': [r['speed_score'] for r in results],
    }

    # Add H1-H6 tags
    for i in range(1, 7):
        data[f'H{i} Tags'] = [r['headings'].get(f'h{i}', 0) for r in results]

    df = pd.DataFrame(data)

    if filetype == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, download_name='seo_comparison_report.csv', as_attachment=True)

    elif filetype == 'excel':
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='SEO Report')

        # Add chart
        workbook = writer.book
        worksheet = writer.sheets['SEO Report']

        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'SEO Score',
            'categories': ['SEO Report', 1, 0, len(df), 0],
            'values': ['SEO Report', 1, 1, len(df), 1],
        })

        chart.set_title({'name': 'SEO Score Comparison'})
        chart.set_x_axis({'name': 'URLs'})
        chart.set_y_axis({'name': 'SEO Score'})
        worksheet.insert_chart('L2', chart)

        writer.close()
        output.seek(0)
        return send_file(output, download_name='seo_comparison_report.xlsx', as_attachment=True)

    return "Invalid file format"





import time

def analyze_speed_insights(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        load_time = round(time.time() - start_time, 2)
        soup = BeautifulSoup(response.text, 'html.parser')

        scripts = soup.find_all('script', src=True)
        stylesheets = soup.find_all('link', rel='stylesheet')

        blocking_js = [s['src'] for s in scripts if 'async' not in s.attrs and 'defer' not in s.attrs]
        blocking_css = [l['href'] for l in stylesheets]

        total_size_kb = len(response.content) / 1024  # size in KB

        viewport_tag = soup.find('meta', attrs={'name': 'viewport'})
        mobile_ready = True if viewport_tag else False

        return {
            'url': url,
            'blocking_js': blocking_js,
            'blocking_css': blocking_css,
            'total_scripts': len(scripts),
            'total_css': len(stylesheets),
            'total_size_kb': round(total_size_kb, 2),
            'load_time': load_time,
            'mobile_ready': mobile_ready
        }

    except Exception as e:
        return {
            'url': url,
            'error': str(e)
        }



@app.route('/premium/speed-insights', methods=['GET', 'POST'])
def speed_insights():
    result = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            result = analyze_speed_insights(url.strip())
    return render_template('speed_insights.html', result=result)

from flask import send_file
from io import BytesIO
import pandas as pd
import xlsxwriter  # required for charting

@app.route('/export_speed_report/<filetype>', methods=['POST'])
def export_speed_report(filetype):
    url = request.form.get('url')
    if not url:
        return "No URL provided."

    result = analyze_speed_insights(url.strip())
    if 'error' in result:
        return f"Error: {result['error']}"

    # Prepare DataFrame
    data = {
        'Metric': [
            'URL', 'Total Scripts', 'Total CSS', 'Blocking JS Files',
            'Blocking CSS Files', 'Estimated Page Size (KB)', 'Estimated Load Time (sec)',
            'Mobile-Ready'
        ],
        'Value': [
            result['url'],
            result['total_scripts'],
            result['total_css'],
            ", ".join(result['blocking_js']) if result['blocking_js'] else "None",
            ", ".join(result['blocking_css']) if result['blocking_css'] else "None",
            result['total_size_kb'],
            result['load_time'],
            "Yes" if result['mobile_ready'] else "No"
        ]
    }

    df = pd.DataFrame(data)

    if filetype == 'excel':
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Speed Report')

        # Add Chart
        workbook = writer.book
        worksheet = writer.sheets['Speed Report']

        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Performance Metrics',
            'categories': ['Speed Report', 1, 0, 6, 0],
            'values':     ['Speed Report', 1, 1, 6, 1],
        })

        chart.set_title({'name': 'Speed Insight Breakdown'})
        chart.set_x_axis({'name': 'Metrics'})
        chart.set_y_axis({'name': 'Values'})
        worksheet.insert_chart('D2', chart)

        writer.close()
        output.seek(0)
        return send_file(output, download_name='speed_insights_report.xlsx', as_attachment=True)

    elif filetype == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, download_name='speed_insights_report.csv', as_attachment=True)

    return "Invalid format."






import random

SEO_QA = [
    ("Why is my page slow?", "Large images, too many scripts, or render-blocking CSS can slow down your site."),
    ("How to improve titles?", "Use primary keywords, keep under 60 characters, and ensure relevance."),
    ("Why is my site not ranking?", "Check keyword targeting, content quality, backlinks, and indexing issues."),
    ("What is an H1 tag?", "It's the main heading for a webpage, important for SEO."),
    ("How to reduce bounce rate?", "Improve page speed, content engagement, and mobile usability."),
    ("How to optimize images for SEO?", "Compress images, use alt text, and proper file names."),
    ("What is schema markup?", "Code that helps search engines understand content better."),
    ("What affects my domain authority?", "Backlinks, content quality, and technical SEO."),
    ("Should I use keywords in URLs?", "Yes, concise and relevant keywords improve SEO."),
    ("What are meta descriptions?", "Summaries that appear in SERPs; they affect click-through rate."),
    ("How to fix broken links?", "Audit using tools like Screaming Frog or Ahrefs and remove or redirect."),
    ("Does HTTPS impact SEO?", "Yes, secure sites are favored by search engines."),
    ("What is keyword cannibalization?", "When multiple pages target the same keyword and compete."),
    ("Is mobile optimization necessary?", "Absolutely. Mobile-first indexing is used by Google."),
    ("What is page speed?", "How fast your content loads — it's critical for SEO and UX."),
    ("How to improve Core Web Vitals?", "Focus on LCP, FID, CLS using tools like PageSpeed Insights."),
    ("Why does content length matter?", "Longer content often ranks better, but relevance is key."),
    ("How to use internal linking?", "Link to relevant pages using keyword-rich anchor text."),
    ("What is robots.txt?", "It tells crawlers which pages/files to access or avoid."),
    ("How often to update content?", "Regularly. Outdated content can hurt rankings."),
    ("What is a sitemap?", "A file that lists all URLs to help search engines crawl your site."),
    ("How to get quality backlinks?", "Create share-worthy content and build relationships."),
    ("Why is alt text important?", "It helps visually impaired users and supports image SEO."),
    ("How to track SEO performance?", "Use tools like Google Analytics and Search Console."),
    ("What is canonicalization?", "Avoids duplicate content by defining the preferred URL."),
    ("Does bounce rate affect SEO?", "Indirectly, yes. High bounce rates suggest low relevance."),
    ("Should I block pages from indexing?", "Yes, for low-value or duplicate pages using robots.txt or meta tags."),
    ("How to improve crawl budget?", "Fix broken links, reduce redirects, and optimize structure."),
    ("How to write SEO-friendly URLs?", "Keep them short, include keywords, and use hyphens."),
    ("What is structured data?", "JSON-LD code that enhances rich results in SERPs."),
    ("How to handle duplicate content?", "Use canonical tags or consolidate similar pages."),
    ("How to optimize for featured snippets?", "Answer questions concisely and format content properly."),
    ("What is a backlink?", "A link from another site pointing to your own."),
    ("What is anchor text?", "The visible, clickable text in a hyperlink."),
    ("What is domain authority?", "A score predicting how well a site will rank."),
    ("How does mobile-first indexing work?", "Google uses mobile version of content for ranking."),
    ("Why are internal links important?", "They guide crawlers and distribute authority."),
    ("Does page experience affect SEO?", "Yes, Google includes it in its ranking signals."),
    ("Should I use pop-ups?", "Limit them; intrusive interstitials can hurt rankings."),
    ("What is a noindex tag?", "Tells search engines not to index a page."),
    ("How to improve title tags?", "Use keywords early, keep it readable and unique."),
    ("What’s the ideal keyword density?", "There’s no exact %, just write naturally."),
    ("What is thin content?", "Pages with little value; bad for SEO."),
    ("How often should I blog?", "At least weekly to stay active and crawlable."),
    ("Can I rank without backlinks?", "Rarely. Backlinks are a core ranking factor."),
    ("What is local SEO?", "Optimizing to appear in local search results."),
    ("What is user intent?", "The reason behind a search — informational, transactional, etc."),
    ("Do redirects affect SEO?", "Proper 301 redirects preserve link equity."),
    ("What is mobile responsiveness?", "Your site adapts to different device screens."),
    ("How to optimize blog posts?", "Use keywords, headings, media, and internal links."),
]

@app.route('/premium/seo-chatbot', methods=['GET', 'POST'])
def seo_chatbot():
    if 'chat_history' not in session:
        session['chat_history'] = []
        session['remaining_qs'] = SEO_QA.copy()
        random.shuffle(session['remaining_qs'])

    chat_history = session.get('chat_history', [])
    remaining_qs = session.get('remaining_qs', [])

    if request.method == 'POST':
        question = request.form.get('question')
        if question:
            answer = next((a for q, a in SEO_QA if q == question), "Let me think...")
            chat_history.append({'q': question, 'a': answer})
            session['chat_history'] = chat_history
            # Remove used question
            session['remaining_qs'] = [qa for qa in remaining_qs if qa[0] != question]
            remaining_qs = session['remaining_qs']

    # Show next 5 suggestions
    suggestions = remaining_qs[:5] if remaining_qs else []

    return render_template("seo_chatbot.html", chat_history=chat_history, suggestions=suggestions)




import pandas as pd
from io import BytesIO
from flask import send_file

@app.route('/export_chat/<filetype>')
def export_chat(filetype):
    chat = session.get('chat_history', [])
    if not chat:
        return "No chat history to export."

    # ✅ Rename columns
    df = pd.DataFrame(chat)
    df.rename(columns={'question': 'Questions', 'answer': 'Answer'}, inplace=True)

    if filetype == 'excel':
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, index=False, sheet_name='Chat History')

        # Optional Chart: Answer length chart
        workbook = writer.book
        worksheet = writer.sheets['Chat History']
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Answer Length',
            'categories': ['Chat History', 1, 0, len(df), 0],  # Questions
            'values':     ['Chat History', 1, 1, len(df), 1],  # Answer (length)
        })
        chart.set_title({'name': 'Length of Answers'})
        chart.set_x_axis({'name': 'Questions'})
        chart.set_y_axis({'name': 'Answer Length'})
        worksheet.insert_chart('D2', chart)

        writer.close()
        output.seek(0)
        return send_file(output, download_name='seo_chat_report.xlsx', as_attachment=True)

    elif filetype == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, download_name='seo_chat_report.csv', as_attachment=True)

    return "Unsupported file type."



from textstat import flesch_reading_ease
from bs4 import BeautifulSoup
import requests
import re
from flask import render_template, request, flash

def generate_readability_tips(text):
    tips = []

    sentences = re.split(r'[.!?]', text)
    long_sentences = [s for s in sentences if len(s.split()) > 20]
    if long_sentences:
        tips.append(f"✏️ Avoid long sentences: Found {len(long_sentences)} sentences with more than 20 words.")

    passive_voice = re.findall(r'\b(is|are|was|were|be|been|being)\s+\w+ed\b', text)
    if passive_voice:
        tips.append(f"🎯 Reduce passive voice: Detected {len(passive_voice)} possible usages.")

    if text.count('!') > 3:
        tips.append("⚠️ Too many exclamation marks can make content look unprofessional.")

    if 'click here' in text.lower():
        tips.append("🔗 Replace generic anchor text like 'click here' with descriptive links.")

    if not re.search(r'<h1>.*</h1>', text, re.IGNORECASE):
        tips.append("📌 Add an <h1> heading to help structure your content.")

    return tips

@app.route('/premium/readability', methods=['GET', 'POST'])
def content_readability():
    result = None
    url = None
    if request.method == 'POST':
        url = request.form.get('url')
        try:
            res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            body_text = soup.get_text(separator=' ', strip=True)
            score = flesch_reading_ease(body_text)

            tips = generate_readability_tips(body_text)

            result = {
                'url': url,
                'flesch_score': round(score, 2),
                'tips': tips
            }

        except Exception as e:
            flash(f"Error fetching or analyzing the content: {e}", "danger")

    return render_template("readability.html", result=result)




# @app.route("/premium-features")
# def premium_features():
#     return render_template("premium_features.html")




# ADMIN PANEL

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "krushank123"

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")

        print("DEBUG - Username:", username)
        print("DEBUG - Password:", password)

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            print("✅ Login successful")
            return redirect('/admin/dashboard')
        else:
            print("❌ Invalid login")
            flash("Invalid credentials", "danger")

    return render_template("admin_login.html")








@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, email, subscription_ends FROM users WHERE plan = 'premium'")
    premium_users = [dict(id=row[0], username=row[1], email=row[2], subscription_ends=row[3]) for row in cursor.fetchall()]

    cursor.execute("SELECT id, username, email FROM users WHERE plan = 'free'")
    free_users = [dict(id=row[0], username=row[1], email=row[2]) for row in cursor.fetchall()]

    conn.close()

    return render_template("admin_dashboard.html", premium_users=premium_users, free_users=free_users)




from datetime import datetime, timedelta

@app.route('/admin/upgrade', methods=['POST'])
def admin_upgrade():
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')

    user_id = request.form.get('user_id')
    months = int(request.form.get('plan_duration', 1))

    subscription_end = datetime.now() + timedelta(days=30 * months)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET plan = 'premium', subscription_ends = %s WHERE id = %s", (subscription_end.strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()

    flash(f"User upgraded for {months} month(s).", "success")
    return redirect("/admin/dashboard")






@app.route('/admin/downgrade', methods=['POST'])
def admin_downgrade():
    user_id = request.form.get('user_id')
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET plan = 'free', subscription_ends = NULL WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()
    flash("User downgraded to free.", "info")
    return redirect('/admin/dashboard')




@app.route("/admin/delete", methods=["POST"])
def admin_delete_user():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    user_id = request.form.get("user_id")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    cursor.execute("DELETE FROM analyses WHERE user_id = %s", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted successfully.", "danger")
    return redirect("/admin/dashboard")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect("/admin/login")




from datetime import datetime

@app.before_request
def downgrade_expired_subscriptions():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all premium users with expired subscriptions
    cursor.execute("""
    SELECT id FROM users
    WHERE plan = 'premium'
    AND subscription_ends IS NOT NULL
    AND subscription_ends < CURRENT_TIMESTAMP
""")

    expired_users = cursor.fetchall()

    # Downgrade each expired user
    for (user_id,) in expired_users:
        cursor.execute("UPDATE users SET plan = 'free' WHERE id = %s", (user_id,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    from os import environ
    app.run(host="0.0.0.0", port=int(environ.get("PORT", 5000)))