# Five Guys Scraper

A Python data pipeline for collecting public Five Guys location, menu, Classic Combo, milkshake mix-in, and Google Maps review data into CSV and JSON outputs.

The scraper is built for long-running reliability: it writes rows incrementally, uses menu JSON as the source of truth, bounds optional page-render work, retries failed stores, and saves terminal logs for audit/debugging.

## What It Collects

- Store locations, addresses, hours, services, payment methods, and Google Maps IDs
- Menu items and pricing from Five Guys order menu JSON
- Classic Combo option rows for stores where Classic Combo appears in menu JSON
- Milkshake mix-ins through direct modifier JSON when available
- Google Maps reviews, ratings, and review counts

## Requirements

- Windows 10/11
- Python 3.11
- Google Chrome
- A VPN may be required if `order.fiveguys.com` is unavailable from your region

Install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Quick Start

Smoke test with 10 California stores and 5 reviews per store:

```powershell
$env:FIVE_GUYS_DIRECTORY_ROOT_URL="https://restaurants.fiveguys.com/ca"
$env:FIVE_GUYS_MAX_LOCATIONS="10"
$env:SCRAPER_MODE="full_with_reviews"
$env:GOOGLE_MAPS_REVIEW_LIMIT="5"

$env:SCRAPE_CONCURRENCY="3"
$env:GOOGLE_MAPS_SCRAPE_CONCURRENCY="2"
$env:CLASSIC_COMBO_DETAIL_CONCURRENCY="1"

.\.venv\Scripts\python.exe .\scraper.py
```

Full US run:

```powershell
$env:FIVE_GUYS_DIRECTORY_ROOT_URL="https://restaurants.fiveguys.com/index.html"
$env:FIVE_GUYS_MAX_LOCATIONS="0"
$env:SCRAPER_MODE="full_with_reviews"
$env:GOOGLE_MAPS_REVIEW_LIMIT="100"

$env:SCRAPE_CONCURRENCY="3"
$env:GOOGLE_MAPS_SCRAPE_CONCURRENCY="2"
$env:CLASSIC_COMBO_DETAIL_CONCURRENCY="1"
$env:SCRAPE_LOCATION_TIMEOUT_SECONDS="480"

.\.venv\Scripts\python.exe .\scraper.py
```

## Useful Modes

- `full`: locations, menus, Classic Combo, and milkshake mix-ins
- `full_with_reviews`: core scrape plus Google Maps reviews
- `google_reviews`: rerun Google reviews from saved `locations.csv`/`locations.json`
- `classic_combo`: rerun Classic Combo recovery from saved location/menu outputs
- `failed_stores`: retry store-level rows from `scrape_failures.csv`
- `failed_stores_with_reviews`: retry failed stores and collect reviews only for recovered stores

## Output Files

- `locations.csv` / `locations.json`
- `menu_items.csv` / `menu_items.json`
- `classic_combo_items.csv` / `classic_combo_items.json`
- `milkshake_mixin_items.csv` / `milkshake_mixin_items.json`
- `google_reviews.csv` / `google_reviews.json`
- `scrape_failures.csv`
- `logs/scraper-*.log`

Large output files are ignored by Git by default. Share them with clients separately as deliverables, not as normal source-control files.

## Sample Outputs

Small CSV samples are included under `examples/sample_outputs/`. Each sample contains the header plus the first five rows from a real completed run:

- `examples/sample_outputs/locations_sample.csv`
- `examples/sample_outputs/menu_items_sample.csv`
- `examples/sample_outputs/classic_combo_items_sample.csv`
- `examples/sample_outputs/milkshake_mixin_items_sample.csv`
- `examples/sample_outputs/google_reviews_sample.csv`
- `examples/sample_outputs/scrape_failures_sample.csv`

## Operational Notes

- Worker Chrome profiles are disposable and recreated automatically.
- The default worker profile root is under `%LOCALAPPDATA%\fiveguys-scraper\chrome-worker-profiles`.
- Avoid running this project inside OneDrive for large jobs. OneDrive can lock old Chrome cache/profile files.
- If a store has fewer Google reviews than `GOOGLE_MAPS_REVIEW_LIMIT`, that usually means Google exposed fewer reviews for that store, not that the scraper failed.
- Terminal output is saved automatically under `logs/`.

## Responsible Use

This project is intended for public web data collection and learning/commercial data-pipeline work. Use conservative concurrency, respect site availability, and comply with applicable laws, platform terms, and client requirements.
