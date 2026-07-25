from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def webhook():
    # Capture the data packet sent by LINE
    body = request.get_json()
    
    # Check if there are events in the packet
    if 'events' in body:
        print(f"Received {len(body['events'])} event(s) from LINE.")
        for event in body['events']:
            # We only care if it's a text message
            if event['type'] == 'message' and event['message']['type'] == 'text':
                user_id = event['source']['userId']
                text = event['message']['text']
                
                print("\n🔔 --- NEW MESSAGE RECEIVED ---")
                print(f"Message/Room : {text}")
                print(f"User ID      : {user_id}")
                print("------------------------------\n")
                
    # Always tell LINE "Message received!" so they don't resend it
    return 'OK', 200

if __name__ == "__main__":
    print("🎧 Listening for LINE messages on port 5000...")
    app.run(host='127.0.0.1', port=5050)