import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 🔧 CONFIG
EMAIL = "adammusser40@gmail.com"
APP_PASSWORD = "uqhffqxxqeclonyw"  # ⚠️ Revoke the exposed one first, then paste new one here
KEYWORDS = ["security", "cyber", "engineer", "analyst"]

# ─────────────────────────────────────────────
# 📡 SOURCE 1: RemoteOK
# ─────────────────────────────────────────────
def fetch_remoteok():
    url = "https://remoteok.com/api"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        jobs = []
        for job in data:
            # First item is a legal notice dict without 'position', skip it
            if not isinstance(job, dict) or "position" not in job:
                continue
            jobs.append({
                "title": job.get("position", ""),
                "company": job.get("company", ""),
                "link": job.get("url") or f"https://remoteok.com/remote-jobs/{job.get('id', '')}",
                "tags": " ".join(job.get("tags") or []),
                "source": "RemoteOK"
            })
        print(f"  RemoteOK: {len(jobs)} jobs fetched")
        return jobs
    except Exception as e:
        print(f"  RemoteOK failed: {e}")
        return []

# ─────────────────────────────────────────────
# 📡 SOURCE 2: Arbeitnow (free, no auth needed)
# ─────────────────────────────────────────────
def fetch_arbeitnow():
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json().get("data", [])
        jobs = []
        for job in data:
            jobs.append({
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "link": job.get("url", ""),
                "tags": " ".join(job.get("tags") or []),
                "source": "Arbeitnow"
            })
        print(f"  Arbeitnow: {len(jobs)} jobs fetched")
        return jobs
    except Exception as e:
        print(f"  Arbeitnow failed: {e}")
        return []

# ─────────────────────────────────────────────
# 📡 SOURCE 3: The Muse (free public API)
# ─────────────────────────────────────────────
def fetch_themuse():
    url = "https://www.themuse.com/api/public/jobs"
    params = {"page": 0, "descending": "true"}
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json().get("results", [])
        jobs = []
        for job in data:
            title = job.get("name", "")
            company = job.get("company", {}).get("name", "")
            link = job.get("refs", {}).get("landing_page", "")
            categories = " ".join(c.get("name", "") for c in job.get("categories", []))
            jobs.append({
                "title": title,
                "company": company,
                "link": link,
                "tags": categories,
                "source": "The Muse"
            })
        print(f"  The Muse: {len(jobs)} jobs fetched")
        return jobs
    except Exception as e:
        print(f"  The Muse failed: {e}")
        return []

# ─────────────────────────────────────────────
# 📡 Aggregate all sources
# ─────────────────────────────────────────────
def fetch_jobs():
    print("\n🔍 Fetching jobs from all sources...")
    all_jobs = []
    all_jobs.extend(fetch_remoteok())
    all_jobs.extend(fetch_arbeitnow())
    all_jobs.extend(fetch_themuse())
    print(f"  Total fetched: {len(all_jobs)} jobs\n")
    return all_jobs

# ─────────────────────────────────────────────
# 🔍 Filter by keywords
# ─────────────────────────────────────────────
def filter_jobs(jobs):
    filtered = []
    for job in jobs:
        text = (job["title"] + " " + job["tags"]).lower()
        if any(kw.lower() in text for kw in KEYWORDS):
            filtered.append(job)
    print(f"✅ {len(filtered)} jobs matched keywords: {KEYWORDS}")
    if not filtered:
        print("⚠️  No keyword matches — returning all jobs as fallback")
        return jobs
    return filtered

# ─────────────────────────────────────────────
# 🧹 Deduplicate by link
# ─────────────────────────────────────────────
def deduplicate(jobs):
    seen = set()
    unique = []
    for job in jobs:
        key = job["link"].strip().rstrip("/")
        if key and key not in seen:
            unique.append(job)
            seen.add(key)
    print(f"📋 {len(unique)} unique jobs after deduplication")
    return unique

# ─────────────────────────────────────────────
# ✉️ Send email
# ─────────────────────────────────────────────
def send_email(jobs):
    if not jobs:
        print("⚠️  No jobs to send.")
        return

    # Plain text body
    text_body = ""
    for job in jobs:
        text_body += f"{job['title']} @ {job['company']} [{job['source']}]\n{job['link']}\n\n"

    # HTML body (nicer in inbox)
    html_rows = ""
    for job in jobs:
        html_rows += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <strong>{job['title']}</strong><br>
            <span style="color:#555;">{job['company']}</span>
          </td>
          <td style="padding:8px;border-bottom:1px solid #eee;color:#888;">{job['source']}</td>
          <td style="padding:8px;border-bottom:1px solid #eee;">
            <a href="{job['link']}" style="color:#1a73e8;">Apply</a>
          </td>
        </tr>"""

    html_body = f"""
    <html><body>
    <h2 style="font-family:Arial,sans-serif;">🔥 Daily Job Alerts — {len(jobs)} matches</h2>
    <table style="border-collapse:collapse;font-family:Arial,sans-serif;width:100%;max-width:700px;">
      <tr style="background:#f5f5f5;">
        <th style="padding:8px;text-align:left;">Role</th>
        <th style="padding:8px;text-align:left;">Source</th>
        <th style="padding:8px;text-align:left;">Link</th>
      </tr>
      {html_rows}
    </table>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔥 Daily Job Alerts — {len(jobs)} new matches"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, APP_PASSWORD)
            server.send_message(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Email failed: {e}")

# ─────────────────────────────────────────────
# 🚀 Main
# ─────────────────────────────────────────────
def main():
    jobs = fetch_jobs()
    jobs = filter_jobs(jobs)
    jobs = deduplicate(jobs)
    send_email(jobs[:15])

if __name__ == "__main__":
    main()
