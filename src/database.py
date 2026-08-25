"""Central MongoDB access for the apartment billing system.

Replaces the old file-based JSON storage in json/ with collections that
mirror the same shapes, so the rest of the code only swaps the storage
backend and keeps its logic untouched.

Collections:
    basic_info      one doc  (_id="current") = basic_info.json
    current_meter   one doc  (_id="current") = current_meter.json {water, electric}
    previous_meter  one doc  (_id="current") = previous_meter.json
    final_bills     one doc per billing_month (history)
    uploaded_urls   one doc per billing_month {room: imgbb_url} (history)
    archives        one doc per billing_month = full monthly snapshot
    tenant_line_ids one doc per room {_id: room, line_user_id}

Configuration comes from .env via python-dotenv:
    MONGODB_URI      the Atlas connection string (required)
    MONGODB_DB_NAME  database name (default: "apartment_bill")
"""

import os
from datetime import datetime, timezone

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "apartment_bill")

CURRENT_ID = "current"


class DataNotFoundError(Exception):
    """Raised when a required document is missing from MongoDB."""


_client = None
_db = None


def get_client():
    """Return the lazy MongoClient singleton (raises if MONGODB_URI unset)."""
    global _client
    if _client is None:
        if not MONGODB_URI:
            raise RuntimeError(
                "MONGODB_URI is not set. Add it to .env, e.g.\n"
                "MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/"
            )
        # certifi's CA bundle avoids "CERTIFICATE_VERIFY_FAILED" on macOS Pythons
        # that don't wire up the system trust store by default.
        _client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
    return _client


def get_db():
    """Return the database handle (collection helpers live on it)."""
    global _db
    if _db is None:
        _db = get_client()[MONGODB_DB_NAME]
    return _db


def ping():
    """Verify Atlas connectivity; returns server info dict."""
    info = get_client().admin.command("ping")
    return info


def close():
    """Close the client so the process can exit cleanly."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client = None
    _db = None


def _now():
    return datetime.now(timezone.utc)


def _strip_meta(doc):
    """Remove Mongo-only fields (_id, timestamps) so callers see the old JSON shape."""
    if doc is None:
        return None
    return {k: v for k, v in doc.items() if k not in ("_id", "created_at", "archived_at")}


def _find_or_raise(collection, filter, label):
    doc = collection.find_one(filter)
    if doc is None:
        raise DataNotFoundError(f"{label} not found in MongoDB collection '{collection.name}'")
    return _strip_meta(doc)


def _replace_single(collection, data, label):
    """Upsert a single-document collection with _id=CURRENT_ID."""
    if data is None:
        raise ValueError(f"Cannot save None into collection '{collection.name}'")
    collection.replace_one(
        {"_id": CURRENT_ID},
        {**data, "_id": CURRENT_ID},
        upsert=True,
    )


def get_basic_info():
    return _find_or_raise(get_db().basic_info, {"_id": CURRENT_ID}, "basic_info")


def save_basic_info(data):
    _replace_single(get_db().basic_info, data, "basic_info")


def get_current_meter():
    return _find_or_raise(get_db().current_meter, {"_id": CURRENT_ID}, "current_meter")


def save_current_meter(data):
    _replace_single(get_db().current_meter, data, "current_meter")


def get_previous_meter():
    return _find_or_raise(get_db().previous_meter, {"_id": CURRENT_ID}, "previous_meter")


def save_previous_meter(data):
    _replace_single(get_db().previous_meter, data, "previous_meter")


def get_current_billing_month():
    try:
        info = get_basic_info()
    except DataNotFoundError:
        return None
    return info.get("billing_month")


def save_final_bills(data, billing_month=None):
    """Upsert one final-bills doc keyed by billing_month (keeps history)."""
    month = data.get("billing_month") or billing_month or get_current_billing_month() or "unknown"
    doc = {**data, "_id": month, "created_at": _now()}
    get_db().final_bills.replace_one({"_id": month}, doc, upsert=True)
    return month


def get_final_bills(billing_month=None):
    """Return the latest final-bills doc, or the one for a specific month."""
    collection = get_db().final_bills
    month = billing_month or get_current_billing_month()
    if month:
        doc = collection.find_one({"_id": month})
        if doc:
            return _strip_meta(doc)
    doc = collection.find_one(sort=[("created_at", -1)])
    if doc is None:
        raise DataNotFoundError("final_bills not found in MongoDB collection 'final_bills'")
    return _strip_meta(doc)


def save_uploaded_urls(data, billing_month=None):
    """Upsert one uploaded-urls doc keyed by billing_month (keeps history)."""
    month = billing_month or get_current_billing_month() or "unknown"
    doc = {**data, "_id": month, "created_at": _now()}
    get_db().uploaded_urls.replace_one({"_id": month}, doc, upsert=True)
    return month


def get_uploaded_urls(billing_month=None):
    """Return the room->URL map of the latest (or given) billing month."""
    collection = get_db().uploaded_urls
    month = billing_month or get_current_billing_month()
    if month:
        doc = collection.find_one({"_id": month})
        if doc:
            return _strip_meta(doc)
    doc = collection.find_one(sort=[("created_at", -1)])
    if doc is None:
        raise DataNotFoundError("uploaded_urls not found in MongoDB collection 'uploaded_urls'")
    return _strip_meta(doc)


def archive_cycle(billing_month, basic_info, current_meter, previous_meter,
                  final_bills, uploaded_urls):
    """Store one full monthly snapshot in the archives collection."""
    doc = {
        "_id": billing_month,
        "basic_info": basic_info,
        "current_meter": current_meter,
        "previous_meter": previous_meter,
        "final_bills": final_bills,
        "uploaded_urls": uploaded_urls,
        "archived_at": _now(),
    }
    get_db().archives.replace_one({"_id": billing_month}, doc, upsert=True)


def list_archive_months():
    """Return billing months that have an archive snapshot, oldest first."""
    return [doc["_id"] for doc in get_db().archives.find(
        {}, {"_id": 1}).sort("archived_at", 1)]


def has_final_bills(billing_month=None):
    """True when a final-bills doc exists for the given (or current) month."""
    month = billing_month or get_current_billing_month()
    if not month:
        return False
    return get_db().final_bills.count_documents({"_id": month}) > 0


def has_uploaded_urls(billing_month=None):
    """True when an uploaded-urls doc exists for the given (or current) month."""
    month = billing_month or get_current_billing_month()
    if not month:
        return False
    return get_db().uploaded_urls.count_documents({"_id": month}) > 0


def set_tenant_line_id(room, user_id):
    get_db().tenant_line_ids.replace_one(
        {"_id": room}, {"_id": room, "line_user_id": user_id}, upsert=True)


def get_tenant_line_id(room):
    doc = get_db().tenant_line_ids.find_one({"_id": room})
    return doc.get("line_user_id") if doc else None


if __name__ == "__main__":
    try:
        info = ping()
        print(f"✅ Connected to MongoDB Atlas: {info}")
        print(f"Database: {MONGODB_DB_NAME}")
    except RuntimeError as error:
        print(f"❌ {error}")
