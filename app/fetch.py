import logging
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"

SOURCES = {
    "mahadbt_schemes.html": "https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData",
    "nsp_home.html": "https://scholarships.gov.in",
    "govt_concession_instructions.pdf": "https://ycce.edu/wp-content/uploads/2025/07/Govt.-Concession-Scheme-Instructions.pdf",
}

HEADERS = {"User-Agent": "ScholarSetu-student-project/0.1 (learning project)"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def download(url, filename, timeout=15):
    """Download one URL into data/raw/. Return True if it worked."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logging.warning("Timed out: %s", url)
        return False
    except requests.exceptions.RequestException as error:
        logging.warning("Failed: %s (%s)", url, error)
        return False

    (RAW_DIR / filename).write_bytes(response.content)
    logging.info("Saved %s (%s bytes)", filename, len(response.content))
    return True


def fetch_all():
    ok = 0
    for filename, url in SOURCES.items():
        if download(url, filename):
            ok += 1
        time.sleep(2)  # be polite: pause between requests
    logging.info("Downloaded %s of %s files", ok, len(SOURCES))
    return ok


if __name__ == "__main__":
    fetch_all()