# ScholarSetu

## Project card
- **Product:** ScholarSetu, a chatbot that matches Maharashtra engineering students to the MahaDBT and NSP/AICTE scholarships they qualify for, with amounts, income limits and deadlines
- **User:** Maharashtra engineering students from reserved and economically weaker categories
- **Problem:** Students apply only for schemes they have heard of, such as EBC, and miss the one meant for their category
- **Data source:** DTE Maharashtra Scholarship Section (https://dte.maharashtra.gov.in) and National Scholarship Portal (https://scholarships.gov.in/All-Scholarships)

## Project structure
```
ScholarSetu/
├── app/
│   ├── cli.py               # menu program that uses records.py
│   ├── fetch.py             # downloads source pages into data/raw/
│   ├── ingest.py            # cleans downloaded pages into data/records.json
│   ├── models.py            # Record dataclass
│   └── records.py           # load_records, search, count_by, get_by_id
├── data/
│   ├── raw/                 # downloaded pages (not pushed to GitHub)
│   ├── records.json         # clean records created by ingest.py
│   └── sample_records.py    # 20 hand-collected schemes
├── day01_intro.py
├── day01_menu.py
├── day02_search.py
├── day03_models_demo.py
├── requirements.txt
└── README.md
```

## Record fields
Each scheme is a dict with: `scheme_name`, `department`, `eligible_category`, `income_limit`, `benefit`, `source_url`, plus `id` and `verified`.
`VERIFY` / `None` means the value has not been collected yet. `verified: true` means it was checked on the official page.

## Day 1
- `day01_intro.py` - prints the project card and asks for name and question
- `day01_menu.py` - menu loop: about, sample questions, eligibility check

## Day 2
- `data/sample_records.py` - 20 hand-collected schemes: 10 from the DTE Maharashtra Scholarship Section and 10 NSP central-sector schemes
- `day02_search.py` - prints all records, searches by keyword, counts records per department and per eligible category
- `app/records.py` - reusable functions: `load_records()`, `search()`, `count_by()`, `get_by_id()`
- `app/cli.py` - menu program that uses the functions in `records.py`

## Day 3
- `app/fetch.py` - downloads the NSP All-Scholarships page and three DTE scheme pages into `data/raw/` with timeouts, retries and error handling
- `app/ingest.py` - parses the downloaded pages into the record fields, skips bad rows with a log message, fills missing fields from the hand-collected records, and saves `data/records.json` (43 records)
- `app/models.py` - `Record` dataclass for one scheme
- `app/records.py` - `load_records()` now reads `data/records.json` (falls back to `sample_records.py`); `load_record_objects()` returns `Record` objects
- `day03_models_demo.py` - converts loaded dicts into `Record` objects

## How to run
Run all commands from the project root folder.

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

    python day01_intro.py
    python day01_menu.py
    python day02_search.py

    python -m app.fetch
    python -m app.ingest
    python -m app.cli
    python day03_models_demo.py

## Notes
- The DTE site sometimes returns a 503 error. `fetch.py` retries and skips files it already has; use `python -m app.fetch --force` to download everything again.
- `records.json` includes NSP schemes that are not for engineering students. They will be filtered later.
- Most scheme details (income limit, benefit, eligibility) are still `VERIFY` and are being filled in from the official pages.