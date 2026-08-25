"""Business-logic layer the Flask API calls.

Each function wraps the existing CLI modules and persists state to MongoDB, so
the web app can drive the whole monthly workflow step by step:
new month -> enter meters -> DRC -> bill/PDF -> JPEG -> ImgBB upload -> LINE send.
"""

from pathlib import Path

import src.database as db
import src.drc as drc
import src.new_cycle as new_cycle
import src.processes as processes
import src.create_bill as create_bill
import src.pdf_to_jpeg as pdf_to_jpeg
import src.upload_imgbb as upload_imgbb
import src.send_line_image as send_line_image

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_PATH = BASE_DIR / "apartment_bill.pdf"
JPEG_DIR = BASE_DIR / "apartment_bill_jpeg"


def _optional(getter):
    try:
        return getter()
    except db.DataNotFoundError:
        return None


def get_uploaded_urls():
    """Current month's room -> ImgBB URL map (empty if none uploaded yet)."""
    if not db.has_uploaded_urls():
        return {}
    return db.get_uploaded_urls()


def get_state():
    """Overall workflow status for the dashboard."""
    info = _optional(db.get_basic_info)
    prev = _optional(db.get_previous_meter)
    curr = _optional(db.get_current_meter)

    rooms_config = (info or {}).get("rooms_config", {})
    jpeg_count = len(list(JPEG_DIR.glob("*.jpg"))) if JPEG_DIR.exists() else 0
    uploaded = get_uploaded_urls()

    drc_issue_count = 0
    if curr and (curr.get("water") or curr.get("electric")):
        try:
            drc_issue_count = len(drc.detect_current_issues())
        except Exception:
            drc_issue_count = 0

    try:
        tenant_count = db.get_db().tenant_line_ids.count_documents({})
    except Exception:
        tenant_count = 0

    return {
        "apartment_name": (info or {}).get("apartment_name"),
        "billing_month": (info or {}).get("billing_month"),
        "bill_date": (info or {}).get("bill_date"),
        "has_basic_info": info is not None,
        "has_previous_meter": prev is not None,
        "has_current_meter": curr is not None,
        "current_rooms_count": len((curr or {}).get("water", [])),
        "current_has_values": bool(curr and ((curr.get("water")) or (curr.get("electric")))),
        "drc_issues": drc_issue_count,
        "bills_generated": db.has_final_bills(),
        "urls_uploaded": db.has_uploaded_urls(),
        "uploaded_count": len(uploaded),
        "jpegs_exist": jpeg_count > 0,
        "jpeg_count": jpeg_count,
        "archives": db.list_archive_months(),
        "tenant_line_id_count": tenant_count,
        "rooms": list(rooms_config.keys()),
        "rooms_config": rooms_config,
    }


def start_new_cycle(billing_month, bill_date):
    """Archive + roll over + set dates, then clear current meters for fresh entry."""
    if not billing_month or not bill_date:
        raise ValueError("billing_month and bill_date are required")
    # Pre-check so we don't roll over an empty state (raises DataNotFoundError).
    db.get_basic_info()
    db.get_current_meter()

    new_cycle.start_new_cycle(billing_month=billing_month, bill_date=bill_date)
    db.save_current_meter({"water": [], "electric": []})
    return get_state()


def get_meters():
    """Previous + current meters in the friendly {room: {water, electric}} shape."""
    prev = _optional(db.get_previous_meter)
    curr = _optional(db.get_current_meter)
    return {
        "previous": processes.meters_to_friendly(prev) if prev else {},
        "current": processes.meters_to_friendly(curr) if curr else {},
    }


def save_current_meters(rooms):
    """Validate and store the new month's readings."""
    if not isinstance(rooms, dict) or not rooms:
        raise ValueError("rooms must be a non-empty object of {room: {water, electric}}")
    for room, vals in rooms.items():
        if not isinstance(vals, dict):
            raise ValueError(f"Invalid reading for room {room}")
        for key in ("water", "electric"):
            try:
                value = int(vals.get(key, 0))
            except (TypeError, ValueError):
                raise ValueError(f"Invalid {key} value for room {room}")
            if value < 0 or value > 9999:
                raise ValueError(f"{key} value {value} out of range 0-9999 for room {room}")

    meter_data = processes.friendly_to_meters(rooms)
    db.save_current_meter(meter_data)
    return get_state()


def detect_drc_issues():
    return drc.detect_current_issues()


def apply_drc_fixes(fixes):
    if not fixes:
        return {"applied": 0, "issues": drc.detect_current_issues()}
    prev_meter = db.get_previous_meter()
    curr_meter = db.get_current_meter()
    applied = drc.apply_fixes(fixes, prev_meter, curr_meter)
    return {"applied": applied, "issues": drc.detect_current_issues()}


def generate_bills_and_pdf():
    """Compute bills, save to MongoDB, and render the PDF invoice."""
    data = processes.get_calculated_bill_data()
    if not data:
        raise ValueError("Could not compute bills — previous and current meters are required.")

    db.save_final_bills(data)
    create_bill.create_apartment_bill_pdf(data, output_filename=str(PDF_PATH))
    return {
        "rooms": len(data["rooms"]),
        "pdf": PDF_PATH.name,
        "total": len(data["rooms"]),
    }


def convert_pdf_to_jpegs():
    if not PDF_PATH.exists():
        raise ValueError("apartment_bill.pdf not found — generate the bill first.")
    files = pdf_to_jpeg.convert_pdf_to_jpeg(PDF_PATH, output_dir=JPEG_DIR, dpi=200, quality=95)
    return {"count": len(files), "dir": JPEG_DIR.name}


def upload_bills():
    """Upload every JPEG to ImgBB and store the public URLs for the current month."""
    if not JPEG_DIR.exists():
        raise ValueError("JPEG folder not found — convert the PDF first.")
    total = len(list(JPEG_DIR.glob("*.jpg")))
    if total == 0:
        raise ValueError("No JPEGs found — convert the PDF first.")

    uploaded = upload_imgbb.upload_all_bills(str(JPEG_DIR))
    if not uploaded:
        raise ValueError("No images were uploaded to ImgBB — check IMGBB_API_KEY and retry.")

    db.save_uploaded_urls(uploaded)
    return {"uploaded": len(uploaded), "total": total}


def send_bills():
    """Send the current month's uploaded bills via LINE (tenants, admin fallback)."""
    urls = get_uploaded_urls()
    if not urls:
        raise ValueError("No uploaded URLs found — upload bills first.")
    return send_line_image.send_bills(urls)
