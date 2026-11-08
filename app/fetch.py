import logging
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

DTE = "https://dte.maharashtra.gov.in"

# filename -> url
SOURCES = {
    # NSP list of all schemes (names, departments and dates only)
    "nsp_all_scholarships.html": "https://scholarships.gov.in/All-Scholarships",
    # The 10 pages of the DTE Maharashtra "Scholarship Section" menu
    "dte_rajarshi.html": f"{DTE}/rajarshi-chhatrapati-shahu-maharaj",
    "dte_panjabrao.html": f"{DTE}/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna",
    "dte_merit_cum_means.html": f"{DTE}/merit-cum-means/",
    "dte_foreign.html": f"{DTE}/foreign-scholarship-2022/",
    "dte_minority.html": f"{DTE}/scholarship-for-students-of-minority-communities-pursuing-higher-and-professional-courses",
    "dte_topclass_swd.html": f"{DTE}/scholarship-for-top-class-education-for-students-with-disabilities",
    "dte_saksham.html": f"{DTE}/saksham-scholarship-scheme",
    "dte_pragati.html": f"{DTE}/pragati-scholarship-scheme/",
    "dte_pg_national.html": f"{DTE}/%E0%A4%AA%E0%A4%A6%E0%A4%B5%E0%A5%8D%E0%A4%AF%E0%A5%81%E0%A4%A4%E0%A5%8D%E0%A4%A4%E0%A4%B0-%E0%A4%AA%E0%A4%A6%E0%A4%B5%E0%A5%80-%E0%A4%85%E0%A4%AD%E0%A5%8D%E0%A4%AF%E0%A4%BE%E0%A4%B8%E0%A4%BE%E0%A4%B8",
    "dte_swanath.html": f"{DTE}/swanath-scholarship-scheme-e",
}

HEADERS = {"User-Agent": "ScholarSetu-student-project/0.1 (learning project)"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def download(url, filename, timeout=15, retries=3):
    """Download one URL into data/raw/, retrying on errors. Return True if it worked."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logging.warning("Timed out (try %s of %s): %s", attempt, retries, url)
        except requests.exceptions.RequestException as error:
            logging.warning("Failed (try %s of %s): %s (%s)", attempt, retries, url, error)
        else:
            (RAW_DIR / filename).write_bytes(response.content)
            logging.info("Saved %s (%s bytes)", filename, len(response.content))
            return True
        time.sleep(2 * attempt)  # wait longer after each failure
    return False


def fetch_all(force=False):
    ok = 0
    for filename, url in SOURCES.items():
        if (RAW_DIR / filename).exists() and not force:
            logging.info("Already have %s (use --force to download again)", filename)
            ok += 1
            continue
        if download(url, filename):
            ok += 1
        time.sleep(2)  # be polite: pause between requests
    logging.info("Have %s of %s files", ok, len(SOURCES))
    return ok


if __name__ == "__main__":
    fetch_all(force="--force" in sys.argv)