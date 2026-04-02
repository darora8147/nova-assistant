"""
job_agent.py
------------
Main orchestrator. Runs the full pipeline:
  1. Load profile
  2. Scrape all platforms
  3. Score + filter jobs
  4. Save to database
  5. Send evening email report

Also runs as a background scheduler:
  - 09:00  → scrape + score + save
  - 19:00  → send email report

Usage:
  python -m job_agent.job_agent           # run once immediately
  python -m job_agent.job_agent --schedule # run on daily schedule
  python -m job_agent.job_agent --report   # send report now
"""

import os
import json
import logging
import argparse
import threading
import schedule
import time
from datetime import datetime
from pathlib import Path

from job_agent.database  import init_db, insert_job, update_score, get_todays_jobs, get_unnotified_jobs, mark_notified, get_stats_today
from job_agent.scrapers  import scrape_all
from job_agent.matcher   import score_all
from job_agent.notifier  import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("job_agent")

PROFILE_PATH = Path(__file__).parent / "profile.json"


def load_profile() -> dict:
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)


# ── Step 1: Scrape + score + save ────────────────────────────────────────────

def run_scrape(profile: dict = None) -> dict:
    """Full scrape pipeline. Returns summary stats."""
    if profile is None:
        profile = load_profile()

    logger.info("=" * 50)
    logger.info("Job Agent starting scrape...")
    logger.info(f"Profile: {profile.get('title')} | {profile.get('relevant_experience_years')}y experience")
    logger.info("=" * 50)

    # 1. Scrape
    logger.info("Step 1/3: Scraping job platforms...")
    jobs = scrape_all(profile)
    logger.info(f"  → {len(jobs)} jobs scraped")

    # 2. Score
    logger.info("Step 2/3: Scoring jobs with AI...")
    use_llm = True
    scored_jobs = score_all(jobs, profile, use_llm=use_llm)
    logger.info(f"  → {len(scored_jobs)} jobs above threshold ({profile.get('match_threshold', 60)}%)")

    # 3. Save to DB (skip duplicates automatically)
    logger.info("Step 3/3: Saving to database...")
    new_count = 0
    for job in scored_jobs:
        inserted = insert_job(job)
        if inserted:
            update_score(job["job_id"], job["match_score"])
            new_count += 1

    stats = get_stats_today()
    logger.info(f"Done! New jobs today: {new_count} | DB total today: {stats['total_found']}")
    return stats


# ── Step 2: Send report ───────────────────────────────────────────────────────

def run_report(profile: dict = None) -> bool:
    """Send the daily email report."""
    if profile is None:
        profile = load_profile()

    jobs  = get_unnotified_jobs()
    stats = get_stats_today()

    if not jobs:
        logger.info("No new jobs to report today.")
        return True

    logger.info(f"Sending report for {len(jobs)} jobs to {profile.get('notify_email')}...")
    success = send_report(jobs, stats, profile)

    if success:
        mark_notified([j["job_id"] for j in jobs])
        logger.info("Report sent and jobs marked as notified.")
    return success


# ── Full daily run ────────────────────────────────────────────────────────────

def run_daily():
    """Scrape + score + save. Report is sent separately at 19:00."""
    try:
        profile = load_profile()
        run_scrape(profile)
        logger.info(f"Next report will be sent at {profile.get('schedule_notify_time', '19:00')}")
    except Exception as e:
        logger.error(f"Daily run failed: {e}", exc_info=True)


def send_daily_report():
    try:
        profile = load_profile()
        run_report(profile)
    except Exception as e:
        logger.error(f"Report sending failed: {e}", exc_info=True)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def start_scheduler():
    """Start the background scheduler. Runs forever."""
    profile = load_profile()
    scrape_time = profile.get("schedule_scrape_time", "09:00")
    notify_time = profile.get("schedule_notify_time", "19:00")

    schedule.every().day.at(scrape_time).do(run_daily)
    schedule.every().day.at(notify_time).do(send_daily_report)

    logger.info(f"Scheduler started.")
    logger.info(f"  Scrape runs daily at:  {scrape_time}")
    logger.info(f"  Report sends daily at: {notify_time}")
    logger.info("  Waiting... (Ctrl+C to stop)")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ── Background thread (used by FastAPI server) ───────────────────────────────

_scheduler_thread: threading.Thread = None

def start_background_scheduler():
    """Launch scheduler in a daemon thread so it runs alongside the web server."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    _scheduler_thread.start()
    logger.info("Job agent scheduler started in background.")


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()

    parser = argparse.ArgumentParser(description="Nova Job Agent")
    parser.add_argument("--schedule", action="store_true", help="Run on daily schedule")
    parser.add_argument("--report",   action="store_true", help="Send report now")
    parser.add_argument("--scrape",   action="store_true", help="Run scrape now (default)")
    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    elif args.report:
        run_report()
    else:
        # Default: run scrape + optionally report
        run_scrape()
        print("\nRun with --report to send email report now.")
        print("Run with --schedule to start the daily scheduler.")
