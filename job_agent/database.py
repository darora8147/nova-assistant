"""
database.py
-----------
SQLite database for storing all scraped jobs.
Tracks: found → scored → applied / skipped
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "job_agent", "jobs.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id      TEXT UNIQUE,          -- platform-specific ID
                platform    TEXT NOT NULL,         -- linkedin / naukri / indeed / internshala
                title       TEXT NOT NULL,
                company     TEXT,
                location    TEXT,
                work_mode   TEXT,
                salary      TEXT,
                experience  TEXT,
                description TEXT,
                url         TEXT,
                match_score INTEGER DEFAULT 0,     -- 0-100
                status      TEXT DEFAULT 'found',  -- found / applied / skipped / failed
                applied_at  TEXT,
                found_at    TEXT DEFAULT (datetime('now', 'localtime')),
                notified    INTEGER DEFAULT 0      -- 0 = not yet in report
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT UNIQUE,
                total_found  INTEGER DEFAULT 0,
                total_scored INTEGER DEFAULT 0,
                total_applied INTEGER DEFAULT 0,
                report_html  TEXT,
                sent_at      TEXT
            )
        """)
        conn.commit()


def job_exists(job_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return row is not None


def insert_job(job: dict) -> bool:
    """Insert a job. Returns True if inserted, False if duplicate."""
    if job_exists(job.get("job_id", "")):
        return False
    with get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO jobs
            (job_id, platform, title, company, location, work_mode,
             salary, experience, description, url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("job_id", ""),
            job.get("platform", ""),
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("work_mode", ""),
            job.get("salary", ""),
            job.get("experience", ""),
            job.get("description", ""),
            job.get("url", ""),
        ))
        conn.commit()
    return True


def update_score(job_id: str, score: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET match_score = ? WHERE job_id = ?",
            (score, job_id)
        )
        conn.commit()


def update_status(job_id: str, status: str):
    applied_at = datetime.now().isoformat() if status == "applied" else None
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = ?, applied_at = ? WHERE job_id = ?",
            (status, applied_at, job_id)
        )
        conn.commit()


def get_todays_jobs(min_score: int = 0) -> list[dict]:
    """Return all jobs found today with score >= min_score."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE date(found_at) = date('now', 'localtime')
            AND match_score >= ?
            ORDER BY match_score DESC
        """, (min_score,)).fetchall()
        return [dict(r) for r in rows]


def get_unnotified_jobs() -> list[dict]:
    """Return all unnotified jobs for today's email report."""
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM jobs
            WHERE notified = 0
            AND date(found_at) = date('now', 'localtime')
            ORDER BY match_score DESC
        """).fetchall()
        return [dict(r) for r in rows]


def mark_notified(job_ids: list[str]):
    with get_conn() as conn:
        conn.executemany(
            "UPDATE jobs SET notified = 1 WHERE job_id = ?",
            [(jid,) for jid in job_ids]
        )
        conn.commit()


def get_stats_today() -> dict:
    with get_conn() as conn:
        today_filter = "date(found_at) = date('now', 'localtime')"
        total  = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {today_filter}").fetchone()[0]
        scored = conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {today_filter} AND match_score > 0").fetchone()[0]
        applied= conn.execute(f"SELECT COUNT(*) FROM jobs WHERE {today_filter} AND status='applied'").fetchone()[0]
        top    = conn.execute(f"SELECT title, company, match_score FROM jobs WHERE {today_filter} ORDER BY match_score DESC LIMIT 5").fetchall()
        return {
            "total_found": total,
            "total_scored": scored,
            "total_applied": applied,
            "top_jobs": [dict(r) for r in top],
        }
