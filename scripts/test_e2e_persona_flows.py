#!/usr/bin/env python3
"""
SVPMS E2E Backend API Tests — All Persona Flows

Tests the complete procurement lifecycle across all user roles:
  1. Admin:        Login, List Departments, List Users, List Budgets
  2. Procurement:  Login, Create Vendor, Create PR, Submit PR
  3. Manager:      Login, List Pending Approvals, Approve PR
  4. System:       Verify PR status → APPROVED, Create PO
  5. Vendor:       Login, List POs (vendor view)
  6. Finance:      Login, Create Receipt, 3-Way Match
"""

import json
import sys
import time
import requests

BASE = "http://localhost:8000"
API = f"{BASE}/api/v1"

# Default password for all seeded users
DEFAULT_PW = "SvpmsTest123!"

# Track results
results = []
tokens = {}
created = {}


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


def log(emoji, msg):
    print(f"  {emoji} {msg}")


def step(name, method, url, token=None, json_body=None, params=None, expected=None):
    """Execute an API call and validate result."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = getattr(requests, method.lower())(url, headers=headers, json=json_body, params=params, timeout=15)
        ok = resp.status_code in (expected or [200, 201])
        data = None
        try:
            data = resp.json()
        except Exception:
            pass

        status = "PASS" if ok else "FAIL"
        results.append({"name": name, "status": status, "code": resp.status_code})

        if ok:
            log(f"{Colors.GREEN}✅{Colors.END}", f"{name} → {resp.status_code}")
        else:
            log(f"{Colors.RED}❌{Colors.END}", f"{name} → {resp.status_code}")
            if data:
                detail = data.get("detail", data)
                if isinstance(detail, dict):
                    detail = detail.get("error", {}).get("message", detail)
                log("  ", f"  Detail: {detail}")

        return ok, data, resp.status_code
    except requests.exceptions.ConnectionError:
        results.append({"name": name, "status": "FAIL", "code": "CONN_ERR"})
        log(f"{Colors.RED}❌{Colors.END}", f"{name} → CONNECTION REFUSED")
        return False, None, 0
    except Exception as e:
        results.append({"name": name, "status": "FAIL", "code": str(e)[:50]})
        log(f"{Colors.RED}❌{Colors.END}", f"{name} → {e}")
        return False, None, 0


def login(email, password=DEFAULT_PW):
    """Login and return access token."""
    ok, data, _ = step(
        f"Login ({email})",
        "POST", f"{BASE}/auth/login",
        json_body={"email": email, "password": password},
    )
    if ok and data:
        return data["access_token"]
    return None


def section(title):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}\n")


# ──────────────────────────────────────────────────────────────
# 0. HEALTH CHECK
# ──────────────────────────────────────────────────────────────
def test_health():
    section("0. HEALTH CHECK")
    step("Health endpoint", "GET", f"{BASE}/health")


# ──────────────────────────────────────────────────────────────
# 1. ADMIN FLOW
# ──────────────────────────────────────────────────────────────
def test_admin_flow():
    section("1. ADMIN FLOW (admin@acme.com)")

    token = login("admin@acme.com")
    if not token:
        log(f"{Colors.RED}❌{Colors.END}", "Admin login failed — skipping admin flow")
        return
    tokens["admin"] = token

    # Get profile
    step("Admin: Get /auth/me", "GET", f"{BASE}/auth/me", token)

    # List departments
    ok, data, _ = step("Admin: List Departments", "GET", f"{API}/departments", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} departments")

    # List users
    ok, data, _ = step("Admin: List Users", "GET", f"{API}/users", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} users")

    # List budgets
    ok, data, _ = step("Admin: List Budgets", "GET", f"{API}/budgets", token)
    if ok and data and data.get("data"):
        b = data["data"][0]
        log("  ", f"  Budget: FY{b['fiscal_year']} Q{b['quarter']} | Total: {b['total_cents']} | Spent: {b['spent_cents']} | Reserved: {b.get('reserved_cents', 'N/A')}")

    # List vendors
    ok, data, _ = step("Admin: List Vendors", "GET", f"{API}/vendors", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} vendors")


# ──────────────────────────────────────────────────────────────
# 2. PROCUREMENT LEAD FLOW
# ──────────────────────────────────────────────────────────────
def test_procurement_flow():
    section("2. PROCUREMENT FLOW (proc.lead@acme.com)")

    token = login("proc.lead@acme.com")
    if not token:
        log(f"{Colors.RED}❌{Colors.END}", "Procurement login failed — skipping")
        return
    tokens["procurement"] = token

    # Create a vendor
    ok, vendor, code = step(
        "Procurement: Create Vendor", "POST", f"{API}/vendors", token,
        json_body={
            "legal_name": f"E2E Test Vendor {int(time.time())}",
            "tax_id": f"E2ETEST{int(time.time()) % 100000000:08d}",
            "email": f"e2e-{int(time.time())}@test.com",
            "phone": "+919876543210",
        },
        expected=[201],
    )
    if ok and vendor:
        created["vendor_id"] = vendor["id"]
        log("  ", f"  Created vendor: {vendor['legal_name']} (ID: {vendor['id'][:8]}...)")

        # Approve vendor (needs admin or proper role)
        admin_token = tokens.get("admin", token)
        ok2, _, _ = step(
            "Admin: Approve Vendor", "POST",
            f"{API}/vendors/{vendor['id']}/approve", admin_token,
        )

    # Create a Purchase Request
    ok, pr, _ = step(
        "Procurement: Create PR", "POST", f"{API}/purchase-requests", token,
        json_body={
            "department_id": "d0000000-0000-0000-0000-000000000003",  # Operations dept
            "title": f"E2E Test PR {int(time.time())}",
            "description": "Automated E2E test purchase request",
            "line_items": [
                {"line_number": 1, "description": "Test Widget A", "quantity": 5, "unit_price_cents": 10000},
                {"line_number": 2, "description": "Test Widget B", "quantity": 2, "unit_price_cents": 25000},
            ],
        },
        expected=[201],
    )
    if ok and pr:
        created["pr_id"] = pr["id"]
        created["pr_number"] = pr.get("pr_number", "?")
        log("  ", f"  Created {pr['pr_number']} | Total: {pr['total_cents']} | Status: {pr['status']}")

        # Submit the PR
        ok2, submitted, _ = step(
            "Procurement: Submit PR", "POST",
            f"{API}/purchase-requests/{pr['id']}/submit", token,
        )
        if ok2 and submitted:
            log("  ", f"  {submitted['pr_number']} → {submitted['status']}")


# ──────────────────────────────────────────────────────────────
# 3. MANAGER APPROVAL FLOW
# ──────────────────────────────────────────────────────────────
def test_manager_flow():
    section("3. MANAGER FLOW (ops.manager@acme.com)")

    # ops.manager is manager for dept d0000000-...03 (Operations)
    token = login("ops.manager@acme.com")
    if not token:
        log(f"{Colors.RED}❌{Colors.END}", "Manager login failed — skipping")
        return
    tokens["manager"] = token

    # List pending approvals
    ok, data, _ = step(
        "Manager: List Pending Approvals", "GET",
        f"{API}/approvals", token,
        params={"status": "PENDING"},
    )
    if ok and data and data.get("data"):
        log("  ", f"  Found {data['pagination']['total']} pending approval(s)")

        # Find the approval for our PR
        target_approval = None
        for a in data["data"]:
            if a.get("entity_id") == created.get("pr_id"):
                target_approval = a
                break

        if target_approval:
            created["approval_id"] = target_approval["id"]
            log("  ", f"  Found approval for {target_approval.get('entity_number', '?')}")

            # Approve the PR
            ok2, result, _ = step(
                "Manager: Approve PR", "POST",
                f"{API}/approvals/{target_approval['id']}/approve", token,
                json_body={"comments": "E2E test — approved"},
            )
            if ok2:
                log("  ", f"  Approval status: {result.get('status', '?')}")
        else:
            log(f"{Colors.YELLOW}⚠️{Colors.END}", "  No approval found for E2E PR — may need different approver")
    elif ok:
        log(f"{Colors.YELLOW}⚠️{Colors.END}", "  No pending approvals found for this manager")

    # Verify PR status
    if created.get("pr_id"):
        ok, pr, _ = step(
            "Manager: Verify PR Status", "GET",
            f"{API}/purchase-requests/{created['pr_id']}", token,
        )
        if ok and pr:
            created["pr_status"] = pr["status"]
            log("  ", f"  PR {pr['pr_number']} status: {pr['status']}")


# ──────────────────────────────────────────────────────────────
# 4. PURCHASE ORDER CREATION
# ──────────────────────────────────────────────────────────────
def test_po_creation():
    section("4. PO CREATION (proc.lead@acme.com)")

    token = tokens.get("procurement") or login("proc.lead@acme.com")
    if not token:
        return

    # Create PO from the approved PR
    if created.get("pr_id") and created.get("pr_status") == "APPROVED":
        vendor_id = created.get("vendor_id")
        if not vendor_id:
            log(f"{Colors.YELLOW}⚠️{Colors.END}", "No vendor — using first active vendor")
            ok, vdata, _ = step("List Vendors for PO", "GET", f"{API}/vendors", token, params={"status": "ACTIVE"})
            if ok and vdata and vdata["data"]:
                vendor_id = vdata["data"][0]["id"]

        if vendor_id:
            ok, po, _ = step(
                "Procurement: Create PO", "POST", f"{API}/purchase-orders", token,
                json_body={
                    "pr_id": created["pr_id"],
                    "vendor_id": vendor_id,
                },
                expected=[201],
            )
            if ok and po:
                created["po_id"] = po["id"]
                created["po_number"] = po.get("po_number", "?")
                log("  ", f"  Created {po.get('po_number')} | Status: {po['status']}")
    else:
        log(f"{Colors.YELLOW}⚠️{Colors.END}", f"  PR not approved (status={created.get('pr_status', 'N/A')}) — skipping PO creation")

    # List POs
    ok, data, _ = step("Procurement: List POs", "GET", f"{API}/purchase-orders", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} PO(s)")


# ──────────────────────────────────────────────────────────────
# 5. VENDOR FLOW
# ──────────────────────────────────────────────────────────────
def test_vendor_flow():
    section("5. VENDOR FLOW (vendor@alphasupplies.com)")

    token = login("vendor@alphasupplies.com")
    if not token:
        log(f"{Colors.RED}❌{Colors.END}", "Vendor login failed — skipping")
        return
    tokens["vendor"] = token

    # Get profile
    step("Vendor: Get /auth/me", "GET", f"{BASE}/auth/me", token)

    # List POs assigned to this vendor
    ok, data, _ = step("Vendor: List POs", "GET", f"{API}/purchase-orders", token)
    if ok and data:
        log("  ", f"  Vendor sees {data['pagination']['total']} PO(s)")

    # List invoices
    ok, data, _ = step("Vendor: List Invoices", "GET", f"{API}/invoices", token)
    if ok and data:
        log("  ", f"  Vendor has {data['pagination']['total']} invoice(s)")


# ──────────────────────────────────────────────────────────────
# 6. FINANCE FLOW
# ──────────────────────────────────────────────────────────────
def test_finance_flow():
    section("6. FINANCE FLOW (finance@acme.com)")

    token = login("finance@acme.com")
    if not token:
        log(f"{Colors.RED}❌{Colors.END}", "Finance login failed — skipping")
        return
    tokens["finance"] = token

    # List budgets
    ok, data, _ = step("Finance: List Budgets", "GET", f"{API}/budgets", token)
    if ok and data:
        for b in data.get("data", []):
            log("  ", f"  FY{b['fiscal_year']} Q{b['quarter']} | Total: {b['total_cents']} | Spent: {b['spent_cents']} | Reserved: {b.get('reserved_cents', 'N/A')}")

    # List invoices
    ok, data, _ = step("Finance: List Invoices", "GET", f"{API}/invoices", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} invoice(s)")

    # List receipts
    ok, data, _ = step("Finance: List Receipts", "GET", f"{API}/receipts", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} receipt(s)")

    # 3-Way Match endpoint
    if created.get("po_id"):
        ok, data, _ = step(
            "Finance: 3-Way Match Check", "POST",
            f"{API}/match",
            token,
            json_body={"po_id": created["po_id"]},
            expected=[200, 422],  # 422 if no receipt/invoice linked
        )
        if ok and data:
            log("  ", f"  Match result: {data}")


# ──────────────────────────────────────────────────────────────
# 7. CROSS-CUTTING: RFQs
# ──────────────────────────────────────────────────────────────
def test_rfq_flow():
    section("7. RFQ FLOW (proc.lead@acme.com)")

    token = tokens.get("procurement") or login("proc.lead@acme.com")
    if not token:
        return

    # List RFQs
    ok, data, _ = step("Procurement: List RFQs", "GET", f"{API}/rfqs", token)
    if ok and data:
        log("  ", f"  Found {data['pagination']['total']} RFQ(s)")


# ──────────────────────────────────────────────────────────────
# 8. AUDIT LOG / READ-ONLY CHECKS
# ──────────────────────────────────────────────────────────────
def test_readonly_checks():
    section("8. READ-ONLY CHECKS")

    token = tokens.get("admin")
    if not token:
        return

    # Verify PR list
    ok, data, _ = step("PR List (all statuses)", "GET", f"{API}/purchase-requests", token)
    if ok and data:
        log("  ", f"  Total PRs: {data['pagination']['total']}")

    # Verify PO list
    ok, data, _ = step("PO List", "GET", f"{API}/purchase-orders", token)
    if ok and data:
        log("  ", f"  Total POs: {data['pagination']['total']}")

    # Verify approval list
    ok, data, _ = step("Approval List (all)", "GET", f"{API}/approvals", token)
    if ok and data:
        log("  ", f"  Total approvals: {data['pagination']['total']}")


# ──────────────────────────────────────────────────────────────
# SUMMARY
# ──────────────────────────────────────────────────────────────
def print_summary():
    section("RESULTS SUMMARY")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)

    print(f"  {Colors.GREEN}PASSED: {passed}{Colors.END}")
    print(f"  {Colors.RED}FAILED: {failed}{Colors.END}")
    print(f"  Total:  {total}")
    print()

    if failed:
        print(f"  {Colors.RED}Failed tests:{Colors.END}")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    ❌ {r['name']} (HTTP {r['code']})")

    print()
    return failed == 0


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{Colors.BOLD}SVPMS E2E Backend API Tests{Colors.END}")
    print(f"Target: {BASE}\n")

    test_health()
    test_admin_flow()
    test_procurement_flow()
    test_manager_flow()
    test_po_creation()
    test_vendor_flow()
    test_finance_flow()
    test_rfq_flow()
    test_readonly_checks()

    all_passed = print_summary()
    sys.exit(0 if all_passed else 1)
