# Apartment Billing CLI

A local command-line tool for producing the monthly bills for my family's apartment buildings.

**This is a personal home-business tool, not a product.** It is built for one operator (me), one apartment business, and one machine. There is no login, no database, no multi-user support, and no deployment target — and it does not need one. The point is to replace a manual spreadsheet-and-invoice routine with something repeatable and harder to get wrong.

---

## What it does

Each month the tool takes a CSV of meter readings and walks through a fixed pipeline:

**archive last month → import meters → check for anomalies → generate PDF bills → split into JPEGs → upload images → send bills over LINE**

Everything runs locally. The only external services are ImgBB (image hosting) and the LINE Messaging API (delivery), and both are optional — you can stop after the JPEG step and send the files manually.

---

## Scope

| | |
| --- | --- |
| **Users** | One — the owner/operator |
| **Business** | My family's apartment buildings |
| **Interface** | Interactive terminal menu |
| **Storage** | Plain JSON files in `json/`, one folder per closed month in `archive/` |
| **Deployment** | None. Run it from the repo root on my laptop |
| **Auth / roles** | None |
| **Multi-tenant** | No |
| **Database** | No |

This is not a SaaS product, a tenant portal, or something intended to be installed on a server. If the requirements ever grow beyond one operator, the JSON storage and the missing auth would be the first things to replace.

---

## Monthly workflow

Run from the repository root:

```bash
python -m src.main
```

The menu is ordered to match the real billing sequence, so the steps are hard to do out of order.

| # | Menu item | What it does | Writes |
| --- | --- | --- | --- |
| 1 | **Start New Billing Cycle** | Copies the four working JSON files into `archive/<billing_month>/`, promotes `current_meter.json` to `previous_meter.json`, and prompts for the new month and bill date. | `archive/`, `json/previous_meter.json`, `json/basic_info.json` |
| 2 | **Import CSV to JSON** | Reads `room`, `water`, `electric` columns and rebuilds `current_meter.json`. | `json/current_meter.json` |
| 3 | **Run DRC (Check Meters)** | Flags negative usage or usage above 500 units, asks about each flagged room, lets me correct the old/new reading, then regenerates the bill data. | `json/previous_meter.json`, `json/current_meter.json`, `json/final_apartment_bills.json` |
| 4 | **Create apartment bill PDF** | Calculates every room's charges and writes one invoice page per room. | `apartment_bill.pdf` |
| 5 | **Convert PDF to JPEG** | Renders each PDF page to a JPEG (200 DPI by default) named after the room. | `apartment_bill_jpeg/` |
| 6 | **Upload JPEGs to ImgBB** | Uploads images in parallel, retries failures, stores the public URLs, and sets a 90-day expiry. | `json/uploaded_urls.json` |
| 7 | **Send bills via LINE** | Pushes each uploaded bill image to my LINE account. | — |
| 8 | **Exit** | | |

### CSV format

The importer is deliberately forgiving: headers are lower-cased and trimmed, and the file is read as `utf-8-sig` so Excel's BOM does not break the first column.

```csv
room,water,electric
101/1,373,4567
102/1,2086,5120
```

- `room` is the unit identifier and is used as the key everywhere else.
- `water` and `electric` must be integers. Invalid rows are skipped with a message rather than aborting the whole import.
- An empty `room` row is ignored.

---

## Billing rules

- **Usage** is `current − previous`. If the current reading is lower than the previous one, the tool assumes a 4-digit meter rollover: `(10000 − previous) + current`.
- Meter values must be between **0 and 9999**.
- A room's bill contains:
  - room rent,
  - water usage × water rate,
  - electricity usage × electricity rate,
  - maintenance fee,
  - optional internet, car-park and back-side charges when configured for that room.
- **Rate precedence** per room: `rooms_config[room]` → top-level `room_water_rates` / `room_electric_rates` → default `water_rate` / `electric_rate`.
- Invoice IDs follow `INV<year><month><6-digit sequence>`, e.g. `INV256910000001` for October 2026 (Buddhist year 2569).
- The DRC treats **more than 500 units** in a month as suspicious, as well as any reading outside **0–9999**. A meter that went backwards is interpreted as a rollover, which also produces a large usage and gets flagged. It does not silently "fix" anything: I confirm each room and either accept the reading or type a corrected value.

---

## Data files

| File | Purpose |
| --- | --- |
| `json/basic_info.json` | Apartment name, address, contact details, current billing month and bill date, default rates, per-room overrides, and `rooms_config` (rent and extra charges per room) |
| `json/previous_meter.json` | Last month's water and electricity readings |
| `json/current_meter.json` | This month's readings, imported from CSV |
| `json/final_apartment_bills.json` | Calculated charges for every room in the current cycle |
| `json/uploaded_urls.json` | Room → public image URL map from the ImgBB step |
| `archive/<MM>-<YYYY>/` | Frozen copy of all four working JSON files for a closed month |
| `archive/apartment_bill_summary_class.csv` | Optional monthly summary generated by `src/summary.py` |

Meter files use a list-of-single-key-objects shape:

```json
{
  "water":    [{ "101/1": 373 }, { "102/1": 2086 }],
  "electric": [{ "101/1": 4567 }, { "102/1": 5120 }]
}
```

The archive is written **before** anything is changed, so a failed import or a bad reading can always be rolled back by copying the archived files back into `json/`.

---

## Setup

**Requirements:** Python 3.12+ (developed on 3.13), pip, and the `Sarabun-Regular.ttf` font that ships in the repo root.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

Run all commands from the repository root. Several paths (`Sarabun-Regular.ttf`, `apartment_bill.pdf`, `json/`, `archive/`) are resolved relative to the working directory or the project root.

### Optional CSV summary

```bash
python -m src.summary
```

Reads every archived month and writes `archive/apartment_bill_summary_class.csv` with per-building totals: room count, water/electric units and amounts, rent, maintenance, internet, parking, other charges, grand total, average per room, and any rooms flagged for review.

---

## Configuration

Create a `.env` file in the repo root. It is gitignored — never commit it.

```dotenv
LINE_CHANNEL_ACCESS_TOKEN=...
ADMIN_LINE_USER_ID=...
IMGBB_API_KEY=...
```

| Variable | Used by | Notes |
| --- | --- | --- |
| `LINE_CHANNEL_ACCESS_TOKEN` | Step 7 | LINE Messaging API channel token |
| `ADMIN_LINE_USER_ID` | Step 7 | The single LINE user that receives the bills |
| `IMGBB_API_KEY` | Step 6 | ImgBB API key |

If any of these are missing, only the relevant step fails; the local billing steps still work.

---

## Project layout

```
src/
  main.py               Interactive menu and the eight workflow steps
  new_cycle.py          Archive the current month and roll meters forward
  csv_to_json.py        CSV → current_meter.json
  drc.py                Meter anomaly review and correction
  processes.py          Usage, rates and charge calculation
  create_bill.py        ReportLab PDF generation with the Thai font
  pdf_to_jpeg.py        PyMuPDF PDF → per-room JPEG conversion
  upload_imgbb.py       Parallel ImgBB upload with retries
  send_line_image.py    LINE image push
  summary.py            Per-building summary of archived months
  plot_electric_usage.py  Experimental usage-distribution chart
  get_line_ids.py       One-off Flask webhook used to discover a LINE user ID
json/                   Live working data for the current cycle
archive/                Closed months
tests/                  Tests from an earlier refactor (see Status)
```

---

## Design decisions

- **Archive before mutating.** Step 1 copies the working files first. Destructive changes only happen after the archive exists.
- **Rollover, not reset.** `current_meter.json` becomes `previous_meter.json`, so the next month always starts from the last known readings.
- **The DRC is interactive on purpose.** A wrong meter reading is a customer-facing problem; guessing silently would be worse than asking.
- **JSON over a database.** For one operator and a hundred-odd rooms, a database would add setup and backup work without solving a real problem. The whole state is readable and diffable.
- **Files are the interface.** The PDF and JPEG names are derived from room numbers, so the images can be checked and sent by hand if the LINE step is skipped.
- **External services are isolated.** ImgBB and LINE live behind small modules; nothing in the billing calculation depends on the network.

---

## Limitations

- Single user, single machine. There is no locking, so do not run two copies against the same folder at once.
- `pdf_to_jpeg.py` maps pages to rooms using a fixed layout: **15 rooms per floor, 4 floors per building**, repeating per building. A change to the building layout requires updating `room_filename_from_page()`.
- Thai invoice labels, page size and column widths are hard-coded in `create_bill.py`.
- Delivery is one-way. There is no read receipt, retry queue or record of which tenants received their bill.
- No automated backup beyond the `archive/` folder. That folder is the backup.
- No deployment tooling (Docker, service files, packaging) by design.

### Status

The tool is in active monthly use. The files in `tests/` are from an earlier refactor and reference modules that no longer exist (`summary2`, `migrate_legacy_archive`); they are kept as reference and are **not** a working test suite. `plot_electric_usage.py` is experimental and not part of the monthly workflow.

---

## Privacy

- `.env` contains API tokens and is gitignored.
- `json/` and `archive/` contain real billing records, including room numbers and amounts.
- Review both folders before sharing this repository or making it public.
