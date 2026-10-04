import requests
import time
import sys

API_URL = "http://127.0.0.1:8000/api/process"
FILE_PATH = "demostandup.mp3"

def main():
    print(f"Uploading {FILE_PATH}...")
    with open(FILE_PATH, "rb") as f:
        files = {"video": f}
        res = requests.post(API_URL, files=files)
        
    if res.status_code != 200:
        print(f"Upload failed: {res.text}")
        sys.exit(1)
        
    job_id = res.json()["job_id"]
    print(f"Upload successful. Job ID: {job_id}")
    
    poll_url = f"{API_URL}/{job_id}"
    while True:
        try:
            r = requests.get(poll_url)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status")
                step = data.get("step")
                print(f"Status: {status} | Step: {step}")
                
                if status == "completed":
                    print("Processing completed successfully!")
                    sys.exit(0)
                elif status == "failed":
                    print(f"Processing failed: {data.get('error')}")
                    sys.exit(1)
            else:
                print(f"Poll failed: {r.status_code} {r.text}")
        except Exception as e:
            print(f"Polling error: {e}")
            
        time.sleep(3)

if __name__ == "__main__":
    main()
