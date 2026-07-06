from pathlib import Path

def convert_pdf_menu():
    try:
        from src.pdf_to_jpeg import convert_pdf_to_jpeg
    except ModuleNotFoundError as error:
        if error.name == "fitz":
            print("Missing dependency: PyMuPDF (fitz).")
            print("Install with: pip install PyMuPDF")
            return
        raise

    default_pdf_path = "apartment_bill.pdf"
    pdf_path = input("Enter PDF file path (press Enter for apartment_bill.pdf): ").strip().strip('"')
    if not pdf_path:
        pdf_path = default_pdf_path

    output_dir = input("Enter output folder (press Enter for default): ").strip().strip('"')
    dpi_input = input("Enter DPI (press Enter for 200): ").strip()
    quality_input = input("Enter JPEG quality 1-100 (press Enter for 95): ").strip()

    try:
        dpi = int(dpi_input) if dpi_input else 200
        quality = int(quality_input) if quality_input else 95
    except ValueError:
        print("DPI and quality must be numbers.")
        return

    try:
        created_files = convert_pdf_to_jpeg(
            Path(pdf_path),
            output_dir=Path(output_dir) if output_dir else None,
            dpi=dpi,
            quality=quality,
        )
    except Exception as error:
        print(f"Conversion failed: {error}")
        return

    print("JPEG files created:")
    for file_path in created_files:
        print(file_path)


def run_drc_menu():
    try:
        from src.drc import main as drc_main
    except Exception as error:
        print(f"Failed to start DRC: {error}")
        return

    try:
        drc_main()
    except EOFError:
        print("DRC canceled (input ended).")


def run_rollover_and_import_menu():
    try:
        from src.new_cycle import start_new_cycle
        from src.csv_to_json import run_csv_to_json_menu
        
        print("\n--- Start New Billing Cycle & Import CSV ---")
        confirm = input("This will archive current data and prepare for the new month. Continue? (Y/N): ").strip().upper()
        
        if confirm == 'Y':
            # 1. Archive the old month and roll over the current meters
            start_new_cycle()
            
            # 2. Prompt for the new CSV to import
            print("\nNow, let's import the new meter readings for the current month.")
            run_csv_to_json_menu()
        else:
            print("Canceled.")
    except Exception as error:
        print(f"Failed to run the combined cycle/import workflow: {error}")


def run_menu():
    while True:
        print("\nSelect an option:")
        print("1. Create apartment bill PDF")
        print("2. Convert PDF to JPEG")
        print("3. Run DRC (Check Meters)")
        print("4. Start New Billing Cycle & Import CSV")
        print("5. Exit")

        try:
            choice = input("Enter choice: ").strip()
        except EOFError:
            print("\nBye.")
            break

        if choice == "1":
            try:
                # Moved import here so it only loads when needed
                from src.processes import get_calculated_bill_data
                from src.create_bill import create_apartment_bill_pdf
                
                data = get_calculated_bill_data()
                if data:
                    create_apartment_bill_pdf(data, "apartment_bill.pdf")
                else:
                    print("Failed to get bill data. Check your JSON files.")
            except Exception as e:
                print(f"Failed to create PDF: {e}")
                
        elif choice == "2":
            convert_pdf_menu()
        elif choice == "3":
            run_drc_menu()
        elif choice == "4":
            run_rollover_and_import_menu()
        elif choice == "5":
            print("Bye.")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    run_menu()