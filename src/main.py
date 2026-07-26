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
        print("\n--- Apartment Billing System ---")
        print("1. Start New Billing Cycle (Archive & Rollover)")
        print("2. Import CSV to JSON")
        print("3. Run DRC (Check Meters)")
        print("4. Create apartment bill PDF")
        print("5. Convert PDF to JPEG")
        print("6. Upload JPEGs to Cloud (ImgBB)")
        print("7. Send Bills via LINE OA")
        print("8. Exit")
        
        choice = input("Enter choice (1-8): ")

        if choice == "1":
            print("\n--- Starting New Cycle ---")
            from src.new_cycle import start_new_cycle
            
            start_new_cycle()
            print("✅ Cycle rolled over and old data archived safely.")

        elif choice == "2":
            print("\n--- Importing CSV ---")
            from src.csv_to_json import run_csv_to_json_menu
            
            run_csv_to_json_menu()
            print("✅ New CSV imported safely.")

        elif choice == "3":
            print("\n--- Running DRC ---")
            from src.drc import main
            
            main()

        elif choice == "4":
            print("\n--- Creating PDF Bills ---")
            from src.processes import get_calculated_bill_data
            from src.create_bill import create_apartment_bill_pdf
            
            data = get_calculated_bill_data()
            create_apartment_bill_pdf(data)
            print("✅ PDFs generated successfully.")

        elif choice == "5":
            print("\n--- Converting PDF to JPEG ---")
            from src.pdf_to_jpeg import convert_pdf_to_jpeg
            
            # Pass the name of your generated PDF file directly into the function
            convert_pdf_to_jpeg("apartment_bill.pdf")
            print("✅ PDFs converted to JPEGs.")

        elif choice == "6":
            print("\n--- ☁️ Uploading JPEGs to ImgBB (Parallel) ---")
            
            # Lazy imports
            import json
            import concurrent.futures
            from pathlib import Path
            from src.upload_imgbb import upload_bill_to_imgbb
            
            jpeg_folder = Path("apartment_bill_jpeg/") 
            url_storage_file = Path("json/uploaded_urls.json")
            
            if not jpeg_folder.exists() or not any(jpeg_folder.iterdir()):
                print(f"❌ No JPEGs found in {jpeg_folder}. Did you run step 5?")
                continue
            
            # 1. Gather and SORT the files so they process in order
            image_files = sorted(jpeg_folder.glob("*.jpg"))
            
            uploaded_data = {}
            print(f"Uploading {len(image_files)} images concurrently. This will be fast!...")
            
            # 2. Define a helper function for the thread pool to execute
            def process_upload(image_path):
                room_number = image_path.stem 
                public_url = upload_bill_to_imgbb(str(image_path))
                return room_number, public_url

            # 3. Use ThreadPoolExecutor to upload in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(process_upload, path): path for path in image_files}
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        room_number, public_url = future.result()
                        if public_url:
                            uploaded_data[room_number] = public_url
                    except Exception as e:
                        print(f"❌ An error occurred during upload: {e}")
            
            # 4. Sort the final dictionary keys just to keep the saved JSON tidy
            uploaded_data = dict(sorted(uploaded_data.items()))

            # 5. Save the URLs to a JSON file for Step 7 to use
            with open(url_storage_file, "w", encoding="utf-8") as f:
                json.dump(uploaded_data, f, indent=4)
                
            print(f"\n✅ All uploads complete! URLs saved to {url_storage_file}")

        elif choice == "7":
            print("\n--- 📱 Sending Bills to Admin via LINE ---")
            import os
            import json
            from pathlib import Path
            from dotenv import load_dotenv
            from src.send_line_image import send_bill_image
            
            load_dotenv()
            admin_user_id = os.getenv('ADMIN_LINE_USER_ID')
            url_storage_file = Path("json/uploaded_urls.json")

            if not admin_user_id:
                print("❌ Error: ADMIN_LINE_USER_ID not found in .env file.")
                continue
                
            if not url_storage_file.exists():
                print(f"❌ Error: {url_storage_file} not found. Please run Step 6 first.")
                continue
                
            # Load the URLs generated in Step 6
            with open(url_storage_file, "r", encoding="utf-8") as f:
                uploaded_data = json.load(f)
                
            if not uploaded_data:
                print("⚠️ No URLs found in the storage file.")
                continue
                
            print(f"Sending bills to Admin ID: {admin_user_id}")
            
            for room_number, public_url in uploaded_data.items():
                print(f"Sending Room {room_number}...")
                send_bill_image(
                    user_id=admin_user_id,
                    original_url=public_url
                )
            
            print("\n✅ All bills successfully sent to the Admin!")

        elif choice == "8":
            print("Exiting system. Have a great day!")
            break
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    run_menu()