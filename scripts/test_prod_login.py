import requests
import sys

URL = "https://svpms-api-bfkj26ioiq-el.a.run.app/auth/login"
USERNAME = "admin@acme.com"
PASSWORD = "SvpmsTest123!"

print(f"Testing login at {URL}...")
try:
    response = requests.post(
        URL,
        data={"username": USERNAME, "password": PASSWORD},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Login SUCCESS!")
        print("Response:", response.json())
        sys.exit(0)
    else:
        print("Login FAILED!")
        print("Response:", response.text)
        sys.exit(1)

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
