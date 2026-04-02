"""
test_gmail.py
-------------
Run this to test Gmail separately before using the full agent.
Usage: python test_gmail.py
"""
import json, smtplib, re
from pathlib import Path

profile  = json.loads(Path("job_agent/profile.json").read_text())
sender   = profile.get("gmail_sender","").strip()
password = profile.get("gmail_app_password","").replace(" ","").strip()
to_email = profile.get("notify_email", sender).strip()

print("\n" + "="*50)
print("  Nova – Gmail Connection Test")
print("="*50)
print(f"  Sender   : {sender}")
print(f"  Send to  : {to_email}")
print(f"  Password : {'*' * len(password)} ({len(password)} chars)")
print("="*50 + "\n")

# Basic validation
errors = []
if not sender:
    errors.append("❌ gmail_sender is empty in profile.json")
if not to_email:
    errors.append("❌ notify_email is empty in profile.json")
if not password:
    errors.append("❌ gmail_app_password is empty in profile.json")
elif len(password) != 16:
    errors.append(f"❌ App password must be exactly 16 chars — yours is {len(password)}")
    errors.append("   Get it from: myaccount.google.com → Security → App Passwords")
if not re.match(r'^[^@]+@gmail\.com$', sender):
    errors.append("❌ gmail_sender must be a @gmail.com address")

if errors:
    for e in errors:
        print(e)
    print("\nFix the above and run again.")
    exit(1)

print("✅ Profile looks valid. Connecting to Gmail...")

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
        server.ehlo()
        print("✅ Connected to smtp.gmail.com:465")
        server.login(sender, password)
        print("✅ Login successful!")

    # Send a real test email
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    msg = MIMEMultipart()
    msg["Subject"] = "✅ Nova Job Agent – Gmail Test"
    msg["From"]    = sender
    msg["To"]      = to_email
    msg.attach(MIMEText(
        "<h2>🤖 Nova is connected!</h2>"
        "<p>Your Gmail is configured correctly. "
        "Daily job reports will be sent to this address.</p>",
        "html"
    ))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
        server.login(sender, password)
        server.sendmail(sender, to_email, msg.as_string())

    print(f"✅ Test email sent to {to_email}")
    print("\n🎉 Gmail is working! Check your inbox.")

except smtplib.SMTPAuthenticationError:
    print("\n❌ Authentication failed. Possible causes:")
    print("   1. You used your regular Gmail password instead of an App Password")
    print("   2. 2-Step Verification is not enabled on your Google account")
    print("   3. The App Password was generated for a different account")
    print("\n   Fix:")
    print("   → Go to myaccount.google.com")
    print("   → Security → 2-Step Verification → turn ON")
    print("   → Security → App Passwords → create one named 'Nova'")
    print("   → Paste the 16-char code into profile.json → gmail_app_password")

except smtplib.SMTPConnectError:
    print("\n❌ Could not connect to Gmail. Check your internet connection.")

except Exception as e:
    print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")
