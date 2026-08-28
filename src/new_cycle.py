import json
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_DIR = BASE_DIR / "json"
ARCHIVE_DIR = BASE_DIR / "archive"

BASIC_INFO_PATH = JSON_DIR / "basic_info.json"
PREV_METER_PATH = JSON_DIR / "previous_meter.json"
CURR_METER_PATH = JSON_DIR / "current_meter.json"
FINAL_BILLS_PATH = JSON_DIR / "final_apartment_bills.json"

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def start_new_cycle():
    if not CURR_METER_PATH.exists():
        print("Error: current_meter.json not found! Cannot start a new cycle.")
        return

    # 1. Get current billing month to name the archive folder
    try:
        info = load_json(BASIC_INFO_PATH)
        month_raw = info.get("billing_month", "unknown_month")
        # Replace slashes so it doesn't create nested directories (e.g., 07/2026 -> 07-2026)
        safe_month_str = month_raw.replace("/", "-") 
    except FileNotFoundError:
        print("Error: basic_info.json not found.")
        return

    # 2. Create archive directory
    cycle_archive_dir = ARCHIVE_DIR / safe_month_str
    cycle_archive_dir.mkdir(parents=True, exist_ok=True)

    # 3. Backup all current files to the archive
    files_to_backup = [
        (PREV_METER_PATH, "previous_meter.json"),
        (CURR_METER_PATH, "current_meter.json"),
        (FINAL_BILLS_PATH, "final_apartment_bills.json"),
        (BASIC_INFO_PATH, "basic_info.json")
    ]

    for file_path, filename in files_to_backup:
        if file_path.exists():
            shutil.copy2(file_path, cycle_archive_dir / filename)

    print(f"Backed up cycle '{month_raw}' files to folder: {cycle_archive_dir}")

    # 4. Roll over current meters to become the new previous meters
    shutil.copy2(CURR_METER_PATH, PREV_METER_PATH)
    print("Rolled over: current_meter.json is now previous_meter.json")

    print("\n" + "="*50)
    print("CYCLE ROLLOVER COMPLETE!")
    print("Next steps for the new month:")
    print(" 1. Update 'billing_month' and 'bill_date' in json/basic_info.json")
    print(" 2. Export your new Excel meter readings to CSV")
    print(" 3. Run 'csv_to_json.py' to generate the new current_meter.json")
    print("="*50)

if __name__ == "__main__":
    confirm = input("Are you sure you want to archive current data and start a new cycle? (Y/N): ").strip().upper()
    if confirm == 'Y':
        start_new_cycle()
    else:
        print("Canceled.")  