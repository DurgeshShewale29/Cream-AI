# ScholarSetu

## Project card
- **Product:** ScholarSetu, a chatbot that matches Maharashtra engineering students to the MahaDBT and NSP/AICTE scholarships they qualify for, with amounts, income limits and deadlines
- **User:** Maharashtra engineering students from reserved and economically weaker categories
- **Problem:** Students apply only for schemes they have heard of, such as EBC, and miss the one meant for their category
- **Data source:** MahaDBT scheme pages (https://mahadbt.maharashtra.gov.in/SchemeData/SchemeData) and National Scholarship Portal (https://scholarships.gov.in)

## Project structure
ScholarSetu/
├── app/
│ ├── records.py # load_records, search, count_by, get_by_id
│ └── cli.py # menu program that uses records.py
├── data/
│ └── sample_records.py # scholarship records (list of dicts)
├── day01_intro.py
├── day01_menu.py
├── day02_search.py
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

## How to run
Run all commands from the project root folder.

    python day01_intro.py
    python day01_menu.py
    python day02_search.py
    python -m app.cli