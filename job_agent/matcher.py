"""
matcher.py
----------
Scores each job 0–100 against your profile using two methods:
  1. Fast keyword scoring (always runs, no LLM needed)
  2. LLM scoring (optional, runs if Ollama is available — richer analysis)

Final score = weighted average of both.
"""

import os
import re
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# ── 1. Fast keyword scorer (no LLM) ─────────────────────────────────────────

def keyword_score(job: dict, profile: dict) -> int:
    """
    Score a job 0-100 based on keyword overlap with your skills.
    Fast and works 100% offline.
    """
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("company", ""),
    ]).lower()

    primary   = [s.lower() for s in profile.get("primary_skills", [])]
    secondary = [s.lower() for s in profile.get("secondary_skills", [])]
    titles    = [t.lower() for t in profile.get("job_titles", [])]
    blocked   = [b.lower() for b in profile.get("blocked_keywords", [])]

    # Instant fail for blocked keywords
    if any(b in text for b in blocked):
        return 0

    score = 0

    # Title match (up to 30 points)
    for t in titles:
        if t in text:
            score += 30
            break
        # partial match
        words = t.split()
        matches = sum(1 for w in words if w in text)
        score += int((matches / max(len(words), 1)) * 20)

    # Primary skills (up to 40 points)
    primary_hits = sum(1 for s in primary if s in text)
    score += int((primary_hits / max(len(primary), 1)) * 40)

    # Secondary skills (up to 20 points)
    secondary_hits = sum(1 for s in secondary if s in text)
    score += int((secondary_hits / max(len(secondary), 1)) * 20)

    # Location / remote bonus (up to 10 points)
    preferred_locs = [l.lower() for l in profile.get("preferred_locations", [])]
    job_loc = job.get("location", "").lower()
    if any(l in job_loc for l in preferred_locs):
        score += 10

    return min(score, 100)


# ── 2. LLM scorer (richer, uses your local Ollama) ──────────────────────────

def llm_score(job: dict, profile: dict) -> int:
    """
    Ask the local LLM to score the job. Returns 0-100 or None on failure.
    This runs only for jobs that already scored >= 40 on keyword scoring
    (no point spending time on clearly irrelevant jobs).
    """
    try:
        import ollama as ol
        prompt = f"""You are a job matching assistant. Score this job for the candidate 0-100.

Candidate profile:
- Title: {profile.get('title')}
- Experience: {profile.get('total_experience_years')} years total, {profile.get('relevant_experience_years')} years relevant
- Primary skills: {', '.join(profile.get('primary_skills', []))}
- Secondary skills: {', '.join(profile.get('secondary_skills', []))}
- Preferred work mode: {', '.join(profile.get('work_mode', []))}

Job details:
- Title: {job.get('title')}
- Company: {job.get('company')}
- Location: {job.get('location')}
- Experience required: {job.get('experience', 'not specified')}
- Description snippet: {job.get('description', '')[:400]}

Respond with ONLY a number between 0 and 100. Nothing else."""

        model = os.getenv("OFFLINE_MODEL", "phi3:mini")
        response = ol.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"num_ctx": 512, "temperature": 0},
        )
        text = response["message"]["content"].strip()
        numbers = re.findall(r'\d+', text)
        if numbers:
            return min(int(numbers[0]), 100)
    except Exception as e:
        logger.debug(f"LLM scoring skipped: {e}")
    return None


# ── Master scorer ─────────────────────────────────────────────────────────────

def score_job(job: dict, profile: dict, use_llm: bool = True) -> int:
    """
    Score a job using keyword matching, optionally enhanced by LLM.
    Returns final score 0-100.
    """
    kw = keyword_score(job, profile)

    if use_llm and kw >= 40:
        llm = llm_score(job, profile)
        if llm is not None:
            # Weighted: 40% keyword + 60% LLM
            return int(kw * 0.4 + llm * 0.6)

    return kw


def score_all(jobs: list[dict], profile: dict, use_llm: bool = True) -> list[dict]:
    """Score all jobs and attach score. Returns sorted by score descending."""
    threshold = profile.get("match_threshold", 60)
    results = []
    for job in jobs:
        score = score_job(job, profile, use_llm=use_llm)
        job["match_score"] = score
        if score >= threshold:
            results.append(job)
        logger.debug(f"  {score:3d}%  {job['title']} @ {job['company']} [{job['platform']}]")

    results.sort(key=lambda j: j["match_score"], reverse=True)
    logger.info(f"Scoring complete: {len(results)}/{len(jobs)} jobs above threshold ({threshold}%)")
    return results
