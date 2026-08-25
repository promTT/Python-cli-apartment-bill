# src/upload_imgbb.py
import concurrent.futures
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_bill_to_imgbb(image_path):
    """
    Uploads a local image file to ImgBB and sets it to auto-delete after 90 days.
    Returns the public HTTPS URL.
    """
    api_key = os.getenv('IMGBB_API_KEY')
    
    if not api_key:
        print("❌ Error: IMGBB_API_KEY not found in .env file.")
        return None

    # ImgBB API endpoint
    url = "https://api.imgbb.com/1/upload"
    
    # 90 days in seconds (60 * 60 * 24 * 90)
    expiration_seconds = 7776000 

    try:
        with open(image_path, "rb") as file:
            # We send the API key and expiration as data, and the file as multipart/form-data
            payload = {
                "key": api_key,
                "expiration": expiration_seconds
            }
            files = {
                "image": file
            }
            
            print(f"Uploading {os.path.basename(image_path)} to ImgBB...")
            response = requests.post(url, data=payload, files=files)
            response.raise_for_status() # Raise an error for bad status codes
            
            # Parse the JSON response to get the URL
            result = response.json()
            public_url = result["data"]["url"]
            
            print(f"✅ Upload successful! URL: {public_url}")
            return public_url

    except FileNotFoundError:
        print(f"❌ Error: Could not find the image file at {image_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to upload to ImgBB: {e}")
        return None


def upload_all_bills(jpeg_dir="apartment_bill_jpeg/", max_workers=20):
    """Upload every *.jpg in jpeg_dir to ImgBB in parallel.

    Returns {room_number: public_url} for the uploads that succeeded.
    """
    folder = Path(jpeg_dir)
    if not folder.exists():
        print(f"❌ JPEG folder not found: {folder}")
        return {}

    image_files = sorted(folder.glob("*.jpg"))
    if not image_files:
        print(f"⚠️ No JPEGs found in {folder}.")
        return {}

    def process_upload(image_path):
        room_number = image_path.stem
        public_url = upload_bill_to_imgbb(str(image_path))
        return room_number, public_url

    uploaded = {}
    print(f"Uploading {len(image_files)} images concurrently...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_upload, path): path for path in image_files}
        for future in concurrent.futures.as_completed(futures):
            try:
                room_number, public_url = future.result()
                if public_url:
                    uploaded[room_number] = public_url
            except Exception as error:
                print(f"❌ An error occurred during upload: {error}")

    return dict(sorted(uploaded.items()))