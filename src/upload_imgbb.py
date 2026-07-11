# src/upload_imgbb.py
import os
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