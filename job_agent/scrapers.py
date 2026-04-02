"""
scrapers.py  (v6)
-----------------
Fix 1: Hard India filter - rejects any job not in India/Remote
Fix 2: Tech stack filter - rejects Java/backend/fullstack mismatches
"""

import hashlib, time, logging, re, json, random, xml.etree.ElementTree as ET
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── India location whitelist ──────────────────────────────────────────────────
INDIA_LOCATIONS = {
    "india", "bangalore", "bengaluru", "mumbai", "pune", "hyderabad",
    "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata",
    "ahmedabad", "jaipur", "chandigarh", "kochi", "trivandrum",
    "remote", "work from home", "wfh", "pan india", "anywhere in india",
    "india remote", "hybrid india",
}

# ── Skills you DO NOT have — reject jobs that require ONLY these ──────────────
REJECT_REQUIRED_SKILLS = [
    # Backend languages
    "java ", "java,", "java.", "java\n", "spring boot", "spring mvc",
    "hibernate", "j2ee", "jee ", ".net ", "c# ", "asp.net",
    "golang", "go lang", "ruby on rails", "php ", "laravel",
    "django", "flask ", "fastapi", "node.js backend", "express.js backend",
    # Mobile
    "android", "ios ", "swift ", "kotlin ", "flutter", "react native",
    # Data/ML
    "machine learning", "data science", "data engineer", "python developer",
    "pyspark", "hadoop", "tableau", "power bi",
    # Backend infra
    "devops", "kubernetes", "docker admin", "aws architect",
]

# ── Skills you DO have — presence of these is a positive signal ───────────────
YOUR_SKILLS = [
    "angular", "react", "javascript", "typescript", "frontend",
    "front-end", "front end", "ui developer", "rxjs", "ngrx",
    "html", "css", "scss", "tailwind", "jest", "ag-grid", "vega",
    "angular material", "web developer",
]

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def _make_id(platform, url):
    return hashlib.md5(f"{platform}:{url}".encode()).hexdigest()

def _hdrs(referer=""):
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        **({"Referer": referer} if referer else {}),
    }

def _get(url, referer="", timeout=20, session=None):
    try:
        r = (session or requests).get(url, headers=_hdrs(referer), timeout=timeout)
        r.raise_for_status()
        return r
    except Exception as e:
        logger.warning(f"GET failed: {url[:80]} — {e}")
        return None


def _is_india_job(job):
    """
    HARD filter — returns True only if location is clearly India or Remote.
    Rejects US, UK, Poland, Germany, Singapore, etc.
    """
    loc = (job.get("location", "") + " " + job.get("work_mode", "")).lower().strip()

    # No location info → keep (will be filtered by score later)
    if not loc:
        return True

    # Explicit non-India countries — reject immediately
    reject_countries = [
        "united states", "usa", "u.s.", "new york", "san francisco", "california",
        "united kingdom", "london", "uk ", " uk,",
        "poland", "warsaw", "germany", "berlin", "france", "paris",
        "singapore", "australia", "sydney", "canada", "toronto",
        "netherlands", "amsterdam", "ireland", "dubai", "uae",
        "sweden", "switzerland", "spain", "italy", "denmark",
    ]
    if any(c in loc for c in reject_countries):
        return False

    # Must contain at least one India indicator
    return any(il in loc for il in INDIA_LOCATIONS)


def _is_relevant_job(job):
    """
    Returns True if job matches frontend profile.
    Rejects Java/backend/fullstack jobs that require non-frontend skills.
    """
    text = (job.get("title", "") + " " + job.get("description", "")).lower()

    # Count how many of YOUR skills appear
    your_hits = sum(1 for s in YOUR_SKILLS if s in text)

    # Check for reject skills — if the title itself contains them, hard reject
    title_lower = job.get("title", "").lower()
    hard_reject_in_title = [
        "java developer", "java engineer", "java architect",
        "backend developer", "back-end developer", "back end developer",
        ".net developer", "fullstack java", "full stack java",
        "android developer", "ios developer", "mobile developer",
        "data engineer", "data scientist", "devops engineer",
        "python developer", "ruby developer", "php developer",
    ]
    if any(r in title_lower for r in hard_reject_in_title):
        return False

    # If job has NO frontend signals at all, reject
    if your_hits == 0:
        return False

    # If job requires Java/backend in description AND has few frontend signals
    reject_hits = sum(1 for r in REJECT_REQUIRED_SKILLS if r in text)
    if reject_hits >= 2 and your_hits <= 1:
        return False

    return True


# ── LinkedIn ──────────────────────────────────────────────────────────────────

def scrape_linkedin(keywords, locations, max_jobs=25):
    jobs, seen = [], set()

    for keyword in keywords[:3]:
        params = {
            "keywords": keyword,
            "location": "India",
            "f_TPR": "r86400",
            "geoId": "102713980",   # LinkedIn India geo ID
            "start": 0,
        }
        url  = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urlencode(params)
        resp = _get(url, referer="https://www.linkedin.com/jobs")
        if not resp:
            continue

        soup  = BeautifulSoup(resp.text, "html.parser")
        for card in soup.find_all("li"):
            try:
                title_el   = card.find("h3") or card.find("a", class_=lambda c: c and "title" in (c or "").lower())
                company_el = card.find("h4")
                loc_el     = card.find("span", class_=lambda c: c and "location" in (c or "").lower())
                link_el    = card.find("a", href=lambda h: h and "linkedin.com/jobs/view" in (h or ""))
                if not link_el:
                    link_el = card.find("a", href=True)
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                if not title or len(title) < 3:
                    continue
                raw_url = link_el.get("href", "").split("?")[0] if link_el else ""
                if not raw_url:
                    continue
                # Normalise to www.linkedin.com so logged-in session works
                job_url = re.sub(r'https?://[a-z-]+\.linkedin\.com', 'https://www.linkedin.com', raw_url)
                uid = _make_id("linkedin", job_url)
                if uid in seen:
                    continue
                loc_text  = loc_el.get_text(strip=True) if loc_el else "India"
                work_mode = "Remote" if "remote" in loc_text.lower() else ""
                job = {
                    "job_id": uid, "platform": "linkedin", "title": title,
                    "company": company_el.get_text(strip=True) if company_el else "",
                    "location": loc_text, "work_mode": work_mode,
                    "salary": "", "experience": "", "description": "", "url": job_url,
                }
                if not _is_india_job(job):
                    continue
                if not _is_relevant_job(job):
                    continue
                seen.add(uid)
                jobs.append(job)
            except Exception:
                continue
        time.sleep(2)
        if len(jobs) >= max_jobs:
            break

    logger.info(f"LinkedIn: {len(jobs)} India frontend jobs")
    return jobs[:max_jobs]


# ── Naukri (RSS feed) ─────────────────────────────────────────────────────────

def scrape_naukri(keywords, locations, max_jobs=25):
    jobs, seen = [], set()
    session = requests.Session()
    try:
        session.get("https://www.naukri.com/", headers=_hdrs(), timeout=8)
        time.sleep(1.5)
    except Exception:
        pass

    for keyword in keywords[:3]:
        kw  = keyword.replace(" ", "%20")
        loc = "india"
        rss = f"https://www.naukri.com/rss/search/rss.php?q={kw}&l={loc}&xp=7%2C13&jobAge=1"
        resp = _get(rss, referer="https://www.naukri.com", session=session)

        if resp and resp.text.strip().startswith("<?xml"):
            try:
                root = ET.fromstring(resp.text)
                for item in root.iter("item"):
                    title   = (item.findtext("title") or "").strip()
                    job_url = (item.findtext("link") or "").strip()
                    desc    = BeautifulSoup(item.findtext("description") or "", "html.parser").get_text()[:300]
                    if not title or not job_url:
                        continue
                    uid = _make_id("naukri", job_url)
                    if uid in seen:
                        continue
                    comp_m = re.search(r'Company\s*:\s*([^\n]+)', desc)
                    loc_m  = re.search(r'Location\s*:\s*([^\n]+)', desc)
                    job = {
                        "job_id": uid, "platform": "naukri", "title": title,
                        "company": comp_m.group(1).strip() if comp_m else "",
                        "location": loc_m.group(1).strip() if loc_m else "India",
                        "work_mode": "Remote" if "remote" in (desc+title).lower() else "",
                        "salary": "", "experience": "", "description": desc, "url": job_url,
                    }
                    if not _is_india_job(job):
                        continue
                    if not _is_relevant_job(job):
                        continue
                    seen.add(uid)
                    jobs.append(job)
            except ET.ParseError:
                pass

        # HTML fallback
        if len(jobs) == 0:
            kw_slug  = re.sub(r'[^a-z0-9]+', '-', keyword.lower()).strip('-')
            html_url = f"https://www.naukri.com/{kw_slug}-jobs-in-india?experience=7-13&jobAge=1"
            resp2 = _get(html_url, referer="https://www.naukri.com/", session=session)
            if resp2:
                soup = BeautifulSoup(resp2.text, "html.parser")
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        d = json.loads(script.string or "")
                        for item in (d if isinstance(d, list) else d.get("itemListElement", [])):
                            j = item.get("item", item)
                            if j.get("@type") != "JobPosting":
                                continue
                            job_url = j.get("url", "")
                            uid = _make_id("naukri", job_url)
                            if uid in seen or not job_url:
                                continue
                            loc_val = j.get("jobLocation", {}).get("address", {}).get("addressLocality", "India")
                            job = {
                                "job_id": uid, "platform": "naukri",
                                "title": j.get("title", ""),
                                "company": j.get("hiringOrganization", {}).get("name", ""),
                                "location": loc_val, "work_mode": "",
                                "salary": "", "experience": "",
                                "description": j.get("description", "")[:300],
                                "url": job_url,
                            }
                            if not _is_india_job(job) or not _is_relevant_job(job):
                                continue
                            seen.add(uid)
                            jobs.append(job)
                    except Exception:
                        continue
        time.sleep(2)

    logger.info(f"Naukri: {len(jobs)} jobs")
    return jobs[:max_jobs]


# ── Indeed via DuckDuckGo ─────────────────────────────────────────────────────

def scrape_indeed(keywords, locations, max_jobs=15):
    jobs, seen = [], set()
    try:
        from duckduckgo_search import DDGS
        time.sleep(5)
        for keyword in keywords[:2]:
            query = f'{keyword} frontend jobs India -java -backend -fullstack -android'
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=10, region="in-en"))
            except Exception as e:
                if "Ratelimit" in str(e):
                    time.sleep(15)
                    with DDGS() as ddgs:
                        results = list(ddgs.text(query, max_results=8, region="in-en"))
                else:
                    results = []

            for r in results:
                url   = r.get("href", "")
                title = r.get("title", "")
                for s in [" - Indeed"," | Indeed"," - Naukri"," | Naukri.com"," - LinkedIn"," | LinkedIn"]:
                    title = title.replace(s, "")
                title = title.strip()
                body  = r.get("body", "")
                if not title or len(title) < 4:
                    continue
                uid = _make_id("ddg", url)
                if uid in seen:
                    continue
                platform = ("naukri" if "naukri.com" in url else
                            "indeed" if "indeed.com" in url else
                            "linkedin" if "linkedin.com" in url else "web")
                job = {
                    "job_id": uid, "platform": platform, "title": title,
                    "company": "", "location": "India",
                    "work_mode": "Remote" if "remote" in (title+body).lower() else "",
                    "salary": "", "experience": "", "description": body[:300], "url": url,
                }
                if not _is_relevant_job(job):
                    continue
                seen.add(uid)
                jobs.append(job)
            time.sleep(3)
            if len(jobs) >= max_jobs:
                break
    except Exception as e:
        logger.warning(f"Indeed/DDG: {e}")

    logger.info(f"Indeed/DDG: {len(jobs)} jobs")
    return jobs[:max_jobs]


# ── Internshala ───────────────────────────────────────────────────────────────

def scrape_internshala(keywords, locations, max_jobs=15):
    jobs, seen = [], set()
    urls = [
        "https://internshala.com/jobs/angular-jobs",
        "https://internshala.com/jobs/react-js-jobs",
        "https://internshala.com/jobs/front-end-development-jobs",
    ]
    for url in urls:
        resp = _get(url, referer="https://internshala.com/jobs")
        if not resp:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(script.string or "")
                for item in (d if isinstance(d, list) else d.get("itemListElement", [])):
                    j = item.get("item", item)
                    if j.get("@type") != "JobPosting":
                        continue
                    job_url = j.get("url", "")
                    uid = _make_id("internshala", job_url)
                    if uid in seen or not job_url:
                        continue
                    job = {
                        "job_id": uid, "platform": "internshala",
                        "title": j.get("title", ""),
                        "company": j.get("hiringOrganization", {}).get("name", ""),
                        "location": j.get("jobLocation", {}).get("address", {}).get("addressLocality", "India"),
                        "work_mode": "", "salary": "", "experience": "",
                        "description": j.get("description", "")[:300],
                        "url": job_url,
                    }
                    if not _is_relevant_job(job):
                        continue
                    seen.add(uid)
                    jobs.append(job)
            except Exception:
                continue
        time.sleep(2)
        if len(jobs) >= max_jobs:
            break

    logger.info(f"Internshala: {len(jobs)} jobs")
    return jobs[:max_jobs]


# ── Master ────────────────────────────────────────────────────────────────────

def scrape_all(profile):
    keywords = profile.get("search_keywords", [])
    locations = profile.get("preferred_locations", ["Remote", "Bangalore", "India"])
    blocked  = [b.lower() for b in profile.get("blocked_keywords", [])]

    all_jobs = []
    all_jobs += scrape_linkedin(keywords, locations)
    all_jobs += scrape_naukri(keywords, locations)
    all_jobs += scrape_indeed(keywords, locations)
    all_jobs += scrape_internshala(keywords, locations)

    # Deduplicate
    seen, unique = set(), []
    for job in all_jobs:
        if job["job_id"] not in seen:
            seen.add(job["job_id"])
            unique.append(job)

    # Blocked keyword filter
    filtered = [
        j for j in unique
        if not any(b in (j["title"] + j.get("description","")).lower() for b in blocked)
    ]

    logger.info(f"Final: {len(filtered)} India frontend jobs")
    return filtered
