import src.database as db
from src.database import DataNotFoundError


def _optional(getter):
    """Return the doc, or None when it is not stored yet (e.g. no uploads)."""
    try:
        return getter()
    except DataNotFoundError:
        return None


def start_new_cycle(billing_month=None, bill_date=None):
    """Archive the current cycle, roll meters over, and set the new month/date.

    When billing_month / bill_date are provided (API), they are used directly;
    otherwise the CLI prompts interactively.
    """
    try:
        info = db.get_basic_info()
        current_meter = db.get_current_meter()
    except DataNotFoundError as error:
        print(f"Error: {error}")
        return

    month_raw = info.get("billing_month", "unknown_month")

    previous_meter = _optional(db.get_previous_meter)
    final_bills = _optional(db.get_final_bills)
    uploaded_urls = _optional(db.get_uploaded_urls)

    # 1. Archive the current cycle into the archives collection (one doc per month)
    db.archive_cycle(
        month_raw,
        basic_info=info,
        current_meter=current_meter,
        previous_meter=previous_meter,
        final_bills=final_bills,
        uploaded_urls=uploaded_urls,
    )
    print(f"📦 Archived cycle '{month_raw}' into MongoDB 'archives' collection.")

    # 2. Roll over current meters to become the new previous meters
    db.save_previous_meter(current_meter)
    print("Rolled over: current_meter is now previous_meter")

    # 3. Update basic_info with the new month and date
    if billing_month is None and bill_date is None:
        # Interactive (CLI) mode
        print("\n" + "-"*50)
        print("Update basic_info for the new cycle")

        current_date = info.get("bill_date", "")
        print(f"Current billing_month : {month_raw}")
        new_month = input(f"Enter new billing_month (or press Enter to keep '{month_raw}'): ").strip()

        print(f"Current bill_date     : {current_date}")
        new_date = input(f"Enter new bill_date (or press Enter to keep '{current_date}'): ").strip()
    else:
        new_month = (billing_month or "").strip()
        new_date = (bill_date or "").strip()

    updated = False
    if new_month:
        info["billing_month"] = new_month
        updated = True
    if new_date:
        info["bill_date"] = new_date
        updated = True

    if updated:
        db.save_basic_info(info)
        print(f"✅ Updated basic_info in MongoDB: month={info['billing_month']}, date={info.get('bill_date')}")
    else:
        print("Kept old dates in basic_info.")

    print("\n" + "="*50)
    print("CYCLE ROLLOVER COMPLETE!")
    print("="*50)

if __name__ == "__main__":
    confirm = input("Are you sure you want to archive current data and start a new cycle? (Y/N): ").strip().upper()
    if confirm == 'Y':
        start_new_cycle()
    else:
        print("Canceled.")
