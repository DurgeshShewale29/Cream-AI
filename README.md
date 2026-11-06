# ScholarSetu

## Project card
- **Product:** ScholarSetu, a chatbot that matches Maharashtra engineering students to the MahaDBT and NSP/AICTE scholarships they qualify for, with amounts, income limits and deadlines
- **User:** Maharashtra engineering students from reserved and economically weaker categories
- **Problem:** Students apply only for schemes they have heard of, such as EBC, and miss the one meant for their category
- **Data source:** MahaDBT scheme pages (https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData) and National Scholarship Portal (https://scholarships.gov.in)

## Project structure
ScholarSetu/
├── app/
│ ├── cli.py # menu program that uses records.py
│ ├── fetch.py # downloads source pages into data/raw/
│ ├── ingest.py # cleans the raw CSV into data/records.json
│ ├── models.py # Record dataclass
│ └── records.py # load_records, search, count_by, get_by_id
├── data/
│ ├── raw/ # downloaded pages (not pushed to GitHub)
│ ├── records.json # clean records created by ingest.py
│ ├── sample_records.py # Day 2 sample records
│ └── scholarships_raw.csv # raw scholarship data
├── day01_intro.py
├── day01_menu.py
├── day02_search.py
├── day03_models_demo.py
├── requirements.txt
└── README.md


## Day 1
- `day01_intro.py` - prints the project card and asks for name and question
- `day01_menu.py` - menu loop: about, sample questions, eligibility check

## Day 2
- `data/sample_records.py` - scholarship records stored as a list of dicts
- `day02_search.py` - prints all records, searches by keyword, counts records per category
- `app/records.py` - reusable functions: `load_records()`, `search()`, `count_by()`, `get_by_id()`
- `app/cli.py` - menu program that uses the functions in `records.py`

## Day 3
- `data/scholarships_raw.csv` - raw scholarship data collected from MahaDBT and NSP
- `app/ingest.py` - cleans each row (income formats, levels, missing fields), skips bad rows with a log message, and saves `data/records.json`
- `app/records.py` - `load_records()` now reads `data/records.json`; `load_record_objects()` returns `Record` objects
- `app/models.py` - `Record` dataclass for one scholarship
- `app/fetch.py` - downloads source pages into `data/raw/` with timeouts and error handling
- `day03_models_demo.py` - converts loaded dicts into `Record` objects

## How to run
Run all commands from the project root folder.

    pip install -r requirements.txt
    python day01_intro.py
    python day01_menu.py
    python day02_search.py
    python -m app.ingest
    python -m app.cli
    python day03_models_demo.py
    python -m app.fetch