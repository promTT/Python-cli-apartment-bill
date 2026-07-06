# Python-cli-apartment-bill
## 📋 How to Use (Workflow)

Run `python3.13 -m src.main` to access the interactive CLI menu. The menu is intentionally ordered chronologically to match your actual billing workflow and prevent skipped steps. Follow these steps each month:

1. **Start New Billing Cycle & Import CSV**: This is a combined safety step. It guarantees that the system always archives the old month's data safely before importing the new month's numbers. It will also prompt you to update the `billing_month` and `bill_date` without needing to open the JSON file manually.
2. **Run DRC (Check Meters)**: Validates the newly imported meters for any anomalies or negative numbers.
3. **Create apartment bill PDF**: Calculates the finalized usage and generates the PDF invoices.
4. **Convert PDF to JPEG**: Splits the PDF into individual image files.

## 📁 Data Requirements

* **CSV Format**: To import new meter readings smoothly, ensure your exported Excel/CSV file has a header row with the columns named `room`, `water`, and `electric` (case-insensitive).
* **JSON Structure**: The system processes meter data in the following format:
```json
{
  "water": [{"1/1": 100}...], 
  "electric": [{"1/1": 200}...]
}

```