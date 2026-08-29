
# src/send_line_image.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

def send_bill_image(user_id, original_url, preview_url=None):
    """
    Sends an image message via LINE Messaging API.
    
    :param user_id: The LINE user ID of the tenant.
    :param original_url: Public HTTPS URL of the full-size JPEG bill.
    :param preview_url: Public HTTPS URL of the preview image (defaults to original_url if not provided).
    """    
    # Fallback to the original image if no smaller preview is provided
    if not preview_url:
        preview_url = original_url

    channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
    
    if not channel_access_token:
        print("❌ Error: LINE_CHANNEL_ACCESS_TOKEN not found in .env file.")
        return False

    api_url = 'https://api.line.me/v2/bot/message/push'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {channel_access_token}'
    }
    
    payload = {
        'to': user_id,
        'messages': [
            {
                'type': 'image',
                'originalContentUrl': original_url,
                'previewImageUrl': preview_url
            }
        ]
    }

    try:
        # Add this temporarily to check what Python is actually seeing
        print(f"DEBUG: Token starts with: {str(channel_access_token)[:15]}...")
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✅ Successfully sent bill image to LINE user: {user_id}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send LINE message: {e}")
        if response is not None:
            print(f"API Response: {response.text}")
        return False