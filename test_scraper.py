"""
test_scraper.py
---------------
Run this to debug scraping per platform.
Usage:  python test_scraper.py
"""
import logging, json
from pathlib import Path
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from job_agent.scrapers import scrape_linkedin, scrape_naukri, scrape_indeed, scrape_internshala

profile   = json.loads(Path("job_agent/profile.json").read_text())
keywords  = profile.get("search_keywords", ["Angular React Frontend Developer"])
locations = profile.get("preferred_locations", ["Remote", "Bangalore"])

print(f"\n{'='*55}")
print(f"  Nova Job Agent – Scraper Test")
print(f"  Keywords : {keywords[:2]}")
print(f"  Locations: {locations[:2]}")
print(f"{'='*55}\n")

def show(name, jobs):
    print(f"\n{'─'*45}")
    print(f"  {name}: {len(jobs)} jobs found")
    print(f"{'─'*45}")
    for j in jobs[:3]:
        print(f"  ✓ [{j['platform']}] {j['title']} @ {j['company']}")
        print(f"      {j['location']} | {j['url'][:70]}")
    if not jobs:
        print("  ✗ No jobs found")

linkedin    = scrape_linkedin(keywords[:2], locations[:2])
show("LinkedIn", linkedin)

naukri      = scrape_naukri(keywords[:2], locations[:2])
show("Naukri", naukri)

indeed      = scrape_indeed(keywords[:2], locations[:2])
show("Indeed", indeed)

internshala = scrape_internshala(keywords[:2], locations[:2])
show("Internshala", internshala)

total = len(linkedin) + len(naukri) + len(indeed) + len(internshala)
print(f"\n{'='*55}")
print(f"  TOTAL: {total} jobs scraped")
print(f"{'='*55}\n")
