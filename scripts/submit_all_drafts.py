import requests
import json
import os

API_URL = "https://svpms-be-gcloud-325948496969.asia-south1.run.app"
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJ0ZW5hbnRfaWQiOiJhMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJyb2xlIjoiYWRtaW4iLCJlbWFpbCI6ImFkbWluQGFjbWUuY29tIiwiaWF0IjoxNzcxNDMzMDk0LCJleHAiOjE3NzE0NTEwOTQsInR5cGUiOiJhY2Nlc3MifQ.Ejva94kz24T1V8AezbsT-p9ZT8LJF4ukoyEfqYi-dcektJ1qORzBvriI7YPct3vxoceWwcGEMFd4i7nJnut-feMyMxZifOOXgMg-gIcXHa8lVqRJJOvPenEx0ZZ2gVqkfoLn72HxOS5gohS99zFKQvwYy_9SkXLR7nyltpkHR7oLVbG3wrdKscxrd5RqyL4aWtGKPFrnha3XyKUGXNVzWXpdyCuQFYSAgLfIwJIdg9iEbxvLn9NXalK2awy-Myxby24gsOrRdR9VEY5jLXawCt5em53LUtwdZ6lyGRyFgBKNX0yR7Iqwj55Ut43Jb8Ad9ye8GAHgBhiHtXykxSJGA76Pni15i1cfcX91EaFxq3ry4PLuNU0TQRN7JfZiAAWQG8G_0d8Wo0aEy3j6kQAiRClEVL093mZtVC4rU1z0XjNR_ClE3P_Q6kBAamJBx2--dOSaG9qQzTG101ZsaM01N_YYipyx9gwjUhwlQdFjdrb30P5Hbh0nTP55OarwvctPfvNTg1q-3ckzSU-xcMV1AX_BsZXJCDTpUdvbMC7ZP7-7XC3uleqIboGCw8b33KmeTUUTOndrMa4ox8DQeVrJk-eN29-7BfcRarzLpUQw4hNUgs6oWCT9KHi6ACrdgtVZ2VY3YzaXGRQHP7V0RZEpGSal0coKre-i7Q10ZN8aLrI"

headers = {"Authorization": f"Bearer {TOKEN}"}

def submit_drafts():
    print("Fetching DRAFT PRs...")
    try:
        res = requests.get(f"{API_URL}/api/v1/purchase-requests", params={"status": "DRAFT", "limit": 20}, headers=headers)
        res.raise_for_status()
        prs = res.json().get("data", [])
        print(f"Found {len(prs)} DRAFT PRs.")
        
        for pr in prs:
            print(f"Submitting PR {pr['pr_number']} ({pr['id']})...")
            submit_res = requests.post(f"{API_URL}/api/v1/purchase-requests/{pr['id']}/submit", headers=headers)
            if submit_res.status_code == 200:
                print(f"  SUCCESS: PR {pr['pr_number']} submitted.")
            else:
                print(f"  FAILED: PR {pr['pr_number']} error: {submit_res.text}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    submit_drafts()
