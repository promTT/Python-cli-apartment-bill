"""One-time migration of the file-based JSON storage into MongoDB Atlas.

Reads the current json/ files into their collections and folds the monthly
snapshots in archive/<month>/ into the archives collection. Idempotent
(upserts), so it is safe to re-run.

Usage:
    python3.13 -m src.migrate_to_mongo

Requires MONGODB_URI in .env (see src/database.py). The local json/ and
archive/ files are left untouched as a read-only backup.
"""

import json
from pathlib import Path

import src.database as db

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_DIR = BASE_DIR / "json"
ARCHIVE_DIR = BASE_DIR / "archive"

CURRENT_FILES = [
    ("basic_info.json", "basic_info"),
    ("current_meter.json", "current_meter"),
    ("previous_meter.json", "previous_meter"),
    ("final_apartment_bills.json", "final_bills"),
    ("uploaded_urls.json", "uploaded_urls"),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def migrate_current_files():
    print("\n--- Current json/ files ---")
    for filename, collection_name in CURRENT_FILES:
        path = JSON_DIR / filename
        if not path.exists():
            print(f"  ⏭  {filename}: not present, skipped")
            continue

        data = load_json(path)

        if collection_name == "basic_info":
            db.save_basic_info(data)
        elif collection_name == "current_meter":
            db.save_current_meter(data)
        elif collection_name == "previous_meter":
            db.save_previous_meter(data)
        elif collection_name == "final_bills":
            db.save_final_bills(data)
        elif collection_name == "uploaded_urls":
            db.save_uploaded_urls(data)

        print(f"  ✅ {filename} -> {collection_name}")


def migrate_archives():
    print("\n--- archive/<month>/ snapshots ---")
    if not ARCHIVE_DIR.exists():
        print("  (no archive folder)")
        return

    folder_count = 0
    for folder in sorted(ARCHIVE_DIR.iterdir()):
        if not folder.is_dir():
            # Legacy archive/*.json meter-only files have no month attribution -> skip.
            continue
        folder_count += 1
        month = _archive_month(folder)
        print(f"  📦 {folder.name} -> archives[{month}]")

        basic_info = _read_optional(folder / "basic_info.json")
        current_meter = _read_optional(folder / "current_meter.json")
        previous_meter = _read_optional(folder / "previous_meter.json")
        final_bills = _read_optional(folder / "final_apartment_bills.json")
        uploaded_urls = _read_optional(folder / "uploaded_urls.json")

        db.archive_cycle(
            month,
            basic_info=basic_info,
            current_meter=current_meter,
            previous_meter=previous_meter,
            final_bills=final_bills,
            uploaded_urls=uploaded_urls,
        )

    if folder_count == 0:
        print("  (no monthly snapshot folders found)")


def _archive_month(folder: Path):
    """Prefer the billing_month inside the archived basic_info, else the folder name."""
    info = _read_optional(folder / "basic_info.json") or {}
    month = info.get("billing_month")
    if month:
        return month
    return folder.name.replace("-", "/")


def _read_optional(path: Path):
    if path.exists():
        return load_json(path)
    return None


def print_summary():
    print("\n--- Verification summary ---")
    db_handle = db.get_db()
    counts = {
        "basic_info": db_handle.basic_info.count_documents({}),
        "current_meter": db_handle.current_meter.count_documents({}),
        "previous_meter": db_handle.previous_meter.count_documents({}),
        "final_bills": db_handle.final_bills.count_documents({}),
        "uploaded_urls": db_handle.uploaded_urls.count_documents({}),
        "archives": db_handle.archives.count_documents({}),
        "tenant_line_ids": db_handle.tenant_line_ids.count_documents({}),
    }
    for name, count in counts.items():
        print(f"  {name:<18}: {count}")

    months = db.list_archive_months()
    if months:
        print(f"\n  Archived months: {', '.join(months)}")
    return counts


def main():
    db.ping()
    print(f"Connected to MongoDB database '{db.MONGODB_DB_NAME}'.")

    migrate_current_files()
    migrate_archives()
    counts = print_summary()

    total = sum(counts.values())
    print(f"\n✅ Migration complete. {total} document(s) stored.")
    print("Local json/ and archive/ files were left untouched as a backup.")
    db.close()


if __name__ == "__main__":
    main()
