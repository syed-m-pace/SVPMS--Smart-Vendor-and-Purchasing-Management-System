#!/usr/bin/env python3
import os
import requests

API_URL = os.getenv("SVPMS_API_URL", "https://svpms-be-gcloud-325948496969.asia-south1.run.app")
ADMIN_EMAIL = os.getenv("SVPMS_ADMIN_EMAIL", "admin@acme.com")
ADMIN_PASSWORD = os.getenv("SVPMS_ADMIN_PASSWORD", "SvpmsTest123!")


def get_token() -> str:
    token = os.getenv("SVPMS_ACCESS_TOKEN")
    if token:
        return token

    resp = requests.post(
        f"{API_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def submit_drafts() -> None:
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    print("Fetching DRAFT PRs...")
    res = requests.get(
        f"{API_URL}/api/v1/purchase-requests",
        params={"status": "DRAFT", "limit": 100},
        headers=headers,
        timeout=20,
    )
    res.raise_for_status()
    prs = res.json().get("data", [])
    print(f"Found {len(prs)} DRAFT PRs.")

    for pr in prs:
        print(f"Submitting PR {pr['pr_number']} ({pr['id']})...")
        submit_res = requests.post(
            f"{API_URL}/api/v1/purchase-requests/{pr['id']}/submit",
            headers=headers,
            timeout=20,
        )
        if submit_res.status_code == 200:
            print(f"  SUCCESS: PR {pr['pr_number']} submitted.")
        else:
            print(f"  FAILED: PR {pr['pr_number']} error: {submit_res.text}")


if __name__ == "__main__":
    submit_drafts()
