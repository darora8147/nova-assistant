"""
notifier.py  (v2 - fixed)
--------------------------
Fix 1: App password works with or without spaces
Fix 2: Send report even when 0 jobs (shows "nothing found today")
Fix 3: Better SMTP error messages
"""

import smtplib, logging, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

logger = logging.getLogger(__name__)


def _clean_password(pw):
    """Accept password with or without spaces — Google allows both."""
    return pw.replace(" ", "").strip()


def _platform_badge(platform):
    colours = {
        "linkedin": "#0077b5", "naukri": "#ff7555",
        "indeed": "#003a9b", "internshala": "#00aeef", "web": "#6b7280",
    }
    c = colours.get(platform.lower(), "#6b7280")
    return (f'<span style="background:{c};color:#fff;font-size:11px;'
            f'padding:2px 8px;border-radius:10px;font-weight:600;">'
            f'{platform.upper()}</span>')


def _score_colour(score):
    return "#22c55e" if score >= 75 else "#f59e0b" if score >= 55 else "#94a3b8"


def build_email_html(jobs, stats, profile):
    today = date.today().strftime("%d %B %Y")
    name  = profile.get("name", "there")
    top   = sorted(jobs, key=lambda j: j.get("match_score", 0), reverse=True)[:15]

    if not top:
        body_content = """
        <div style="text-align:center;padding:40px;color:#64748b;">
          <div style="font-size:48px;margin-bottom:16px;">🔍</div>
          <h2 style="color:#1e293b;">No new jobs found today</h2>
          <p>The agent ran but didn't find any new matching positions.<br>
          Try expanding your search keywords in <code>profile.json</code>.</p>
        </div>"""
    else:
        rows = ""
        for job in top:
            sc = job.get("match_score", 0)
            rows += f"""
            <tr style="border-bottom:1px solid #f1f5f9;">
              <td style="padding:14px 16px;">
                <div style="font-weight:600;color:#1e293b;font-size:14px;">
                  <a href="{job.get('url','#')}" style="color:#1e293b;text-decoration:none;">{job.get('title','—')}</a>
                </div>
                <div style="color:#64748b;font-size:12px;margin-top:3px;">
                  {job.get('company','—')}{' · '+job.get('location','') if job.get('location') else ''}
                  {' · '+job.get('salary','') if job.get('salary') else ''}
                </div>
              </td>
              <td style="padding:14px 16px;text-align:center;">{_platform_badge(job.get('platform',''))}</td>
              <td style="padding:14px 16px;text-align:center;">
                <span style="background:{_score_colour(sc)};color:#fff;font-size:12px;
                  padding:3px 10px;border-radius:10px;font-weight:700;">{sc}%</span>
              </td>
              <td style="padding:14px 16px;text-align:center;">
                <a href="{job.get('url','#')}" style="background:#6366f1;color:#fff;padding:6px 14px;
                  border-radius:6px;font-size:12px;text-decoration:none;font-weight:600;">View →</a>
              </td>
            </tr>"""
        body_content = f"""
        <table style="width:100%;border-collapse:collapse;">
          <thead><tr style="background:#f8fafc;">
            <th style="padding:10px 16px;text-align:left;font-size:11px;color:#94a3b8;text-transform:uppercase;">Role</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;color:#94a3b8;text-transform:uppercase;">Platform</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;color:#94a3b8;text-transform:uppercase;">Match</th>
            <th style="padding:10px 16px;text-align:center;font-size:11px;color:#94a3b8;text-transform:uppercase;">Link</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:700px;margin:0 auto;padding:32px 16px;">
  <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:16px;padding:32px;color:#fff;margin-bottom:24px;text-align:center;">
    <div style="font-size:36px;margin-bottom:8px;">🤖</div>
    <h1 style="margin:0;font-size:22px;font-weight:700;">Nova Job Report · {today}</h1>
    <p style="margin:8px 0 0;opacity:.85;">Frontend Developer · India</p>
  </div>
  <p style="color:#475569;font-size:14px;margin-bottom:20px;">Hi {name}! Here's your daily job summary.</p>
  <div style="display:flex;gap:12px;margin-bottom:24px;">
    <div style="flex:1;background:#fff;border-radius:12px;padding:16px;border:1px solid #e2e8f0;text-align:center;">
      <div style="font-size:28px;font-weight:700;color:#6366f1;">{stats.get('total_found',0)}</div>
      <div style="color:#64748b;font-size:12px;margin-top:4px;">Found</div>
    </div>
    <div style="flex:1;background:#fff;border-radius:12px;padding:16px;border:1px solid #e2e8f0;text-align:center;">
      <div style="font-size:28px;font-weight:700;color:#22c55e;">{stats.get('total_scored',0)}</div>
      <div style="color:#64748b;font-size:12px;margin-top:4px;">Good Matches</div>
    </div>
    <div style="flex:1;background:#fff;border-radius:12px;padding:16px;border:1px solid #e2e8f0;text-align:center;">
      <div style="font-size:28px;font-weight:700;color:#f59e0b;">{len(top)}</div>
      <div style="color:#64748b;font-size:12px;margin-top:4px;">In This Report</div>
    </div>
  </div>
  <div style="background:#fff;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">
    <div style="padding:14px 20px;border-bottom:1px solid #f1f5f9;background:#f8fafc;">
      <h2 style="margin:0;font-size:15px;color:#1e293b;">Top Matching Jobs (India / Remote)</h2>
    </div>
    {body_content}
  </div>
  <p style="color:#94a3b8;font-size:11px;text-align:center;margin-top:20px;">
    Sent by Nova Personal AI Assistant · Edit preferences in <code>job_agent/profile.json</code>
  </p>
</div></body></html>"""


def send_report(jobs, stats, profile):
    sender   = profile.get("gmail_sender", "").strip()
    password = _clean_password(profile.get("gmail_app_password", ""))
    to_email = profile.get("notify_email", sender).strip()

    if not sender:
        logger.error("gmail_sender is empty in profile.json")
        return False
    if not password:
        logger.error("gmail_app_password is empty in profile.json")
        return False
    if len(password) != 16:
        logger.error(f"App password should be 16 chars, got {len(password)}. "
                     "Get it from: myaccount.google.com → Security → App Passwords")
        return False

    today   = date.today().strftime("%d %b %Y")
    subject = f"🤖 Nova Job Report · {stats.get('total_found',0)} found · {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Nova Assistant <{sender}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(build_email_html(jobs, stats, profile), "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        logger.info(f"Report sent to {to_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "\n❌ Gmail authentication failed.\n"
            "   Check:\n"
            "   1. gmail_sender is your full Gmail address\n"
            "   2. gmail_app_password is a 16-char App Password (NOT your Gmail password)\n"
            "   3. Get App Password: myaccount.google.com → Security → App Passwords\n"
            "   4. 2-Step Verification must be ON in your Google account"
        )
        return False
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
