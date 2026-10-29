# src/upload_imgbb.py
import os
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def upload_bill_to_imgbb(image_path, max_retries=3, retry_delay=2):
    """
    Uploads a local image file to ImgBB and sets it to auto-delete after 90 days.
    Retries only this image when an upload fails.

    Returns the public HTTPS URL, or None after all attempts fail.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1")
    if retry_delay < 0:
        raise ValueError("retry_delay cannot be negative")

    api_key = os.getenv('IMGBB_API_KEY')
    
    if not api_key:
        print("❌ Error: IMGBB_API_KEY not found in .env file.")
        return None

    # ImgBB API endpoint
    url = "https://api.imgbb.com/1/upload"
    
    # 90 days in seconds (60 * 60 * 24 * 90)
    expiration_seconds = 7776000 

    for attempt in range(1, max_retries + 1):
        try:
            with open(image_path, "rb") as file:
                payload = {
                    "key": api_key,
                    "expiration": expiration_seconds
                }
                files = {
                    "image": file
                }

                print(
                    f"Uploading {os.path.basename(image_path)} "
                    f"(attempt {attempt}/{max_retries})..."
                )
                response = requests.post(
                    url,
                    data=payload,
                    files=files,
                    timeout=30
                )
                response.raise_for_status()

                result = response.json()
                public_url = result["data"]["url"]

                print(f"✅ Upload successful! URL: {public_url}")
                return public_url

        except FileNotFoundError:
            print(f"❌ Error: Could not find the image file at {image_path}")
            return None
        except (
            requests.exceptions.RequestException,
            KeyError,
            TypeError,
            ValueError,
        ) as e:
            if attempt == max_retries:
                print(
                    f"❌ Failed to upload {os.path.basename(image_path)} "
                    f"after {max_retries} attempts: {e}"
                )
                return None

            print(
                f"⚠️ Upload failed for {os.path.basename(image_path)}: {e}. "
                f"Retrying in {retry_delay} seconds..."
            )
            time.sleep(retry_delay)