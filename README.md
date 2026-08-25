# Python-cli-apartment-bill

Monthly meter-reading and billing automation for an apartment complex, with delivery of bills to tenants via LINE OA.

## 🗄️ MongoDB Setup (first time)

All data lives in MongoDB Atlas now (the old `json/` files are kept on disk as a read-only backup).

1. Install dependencies:
   ```bash
   python3.13 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
2. Add your Atlas connection string to `.env`:
   ```bash
   MONGODB_URI=mongodb+srv://<dbuser>:<dbpassword>@<your-cluster>.mongodb.net/?retryWrites=true&w=majority
   # optional: MONGODB_DB_NAME=apartment_bill   (this is the default)
   ```
   The connection uses `certifi`'s CA bundle, which avoids `CERTIFICATE_VERIFY_FAILED`
   on macOS Python installs.
3. Import the existing JSON data (idempotent — safe to re-run):
   ```bash
   .venv/bin/python -m src.migrate_to_mongo
   ```
4. Check the connection:
   ```bash
   .venv/bin/python -m src.database
   ```

Collections: `basic_info`, `current_meter`, `previous_meter`, `final_bills`,
`uploaded_urls` (each keyed by billing month for history), `archives` (one monthly
snapshot per cycle), `tenant_line_ids` (room → LINE user id, written by the webhook),
and `admins` (allowed web-app logins).

## 🌐 Web App (browser-based workflow)

The same monthly flow can be driven from a React web app instead of the CLI:
**login → start new month → enter meter readings → run DRC → generate bill → upload to ImgBB → send via LINE**.

1. Create an admin account (only usernames in the `admins` collection can log in — no self-registration):
   ```bash
   .venv/bin/python -m src.manage_admins add <username>   # prompts for a password
   .venv/bin/python -m src.manage_admins list
   ```
2. Make sure `.env` has a `SECRET_KEY` (random hex string used to sign login JWTs):
   ```bash
   # generate one with:  python3 -c "import secrets; print(secrets.token_hex(32))"
   SECRET_KEY=<random-hex>
   ```
3. Build the frontend (one-time, and again after frontend changes):
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
4. Start the API server (it also serves the built web app at `/`):
   ```bash
   .venv/bin/python -m src.api       # http://127.0.0.1:5000
   ```
   For development with hot reload instead: `cd frontend && npm run dev` (Vite on
   :5173 proxies `/api` to :5000).
5. Open the URL, log in, and walk the dashboard: **Start new month → Enter meter
   readings → Run DRC → Bill, upload & send**.
6. The LINE webhook now runs on the same server: `POST /webhook` (tenants message
   their room number to register their LINE id). Point your LINE OA webhook URL at
   `https://<your-tunnel>/webhook` instead of the old :5050 server.

## 📋 How to Use (Workflow)

Run `python3.13 -m src.main` to access the interactive CLI menu. The menu is
intentionally ordered chronologically to match your actual billing workflow and
prevent skipped steps. Follow these steps each month:

1. **Start New Billing Cycle & Import CSV**: A combined safety step. Archives the
   old month's data into the `archives` collection, rolls the current meters over
   to become the previous meters, and prompts you to update `billing_month` and
   `bill_date` before importing the new month's readings.
2. **Run DRC (Check Meters)**: Validates the newly imported meters for any
   anomalies, negative numbers, or usage beyond 500 units.
3. **Create apartment bill PDF**: Calculates the finalized usage and generates the PDF invoices.
4. **Convert PDF to JPEG**: Splits the PDF into individual room image files.
5. **Upload JPEGs to Cloud (ImgBB)**: Uploads each room's invoice and stores the public URLs in MongoDB (auto-delete after 90 days).
6. **Send Bills via LINE OA**: Reads the uploaded URLs from MongoDB and pushes each bill to the tenant (or admin).

## 📁 Data Requirements

* **CSV Format**: To import new meter readings smoothly, ensure your exported Excel/CSV file has a header row with the columns named `room`, `water`, and `electric` (case-insensitive).
* **Meter Structure**: The system processes meter data in the following format:
```json
{
  "water": [{"101/1": 100}...],
  "electric": [{"101/1": 200}...]
}
```

## 🔁 Capturing tenant LINE IDs

Run the webhook so tenants can register their room → LINE id mapping:
```bash
.venv/bin/python -m src.get_line_ids   # listens on 127.0.0.1:5050
ssh -R 80:127.0.0.1:5050 serveo.net
```
Each tenant sends their room number as a message; the mapping is saved to the
`tenant_line_ids` collection.
