import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def fetch_html(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None

def audit_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)
    report = []

    for link in links:
        href = urljoin(base_url, link['href'])
        text = link.get_text(strip=True) or "(no text)"
        rel = link.get('rel', [])
        is_nofollow = 'nofollow' in rel
        dofollow = not is_nofollow

        try:
            link_resp = requests.head(href, allow_redirects=True, timeout=5)
            is_broken = link_resp.status_code >= 400
        except requests.RequestException:
            is_broken = True

        report.append({
            'text': text,
            'url': href,
            'nofollow': is_nofollow,
            'dofollow': dofollow,
            'broken': is_broken
        })

    return report

def save_audit_to_db(user_id, url, audit_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    for entry in audit_data:
        cursor.execute("""
            INSERT INTO link_audit (user_id, url, link_text, link_url, nofollow, dofollow, broken)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, url, entry['text'], entry['url'], int(entry['nofollow']), int(entry['dofollow']), int(entry['broken'])))
    conn.commit()
    conn.close()