# ai-generated: 100% - Gemini
import urllib.request
import json
import sys

BASE_URL = "http://svcdesk:8080"

def run_tests():
    passed = 0
    failed = 0

    def assert_test(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"[PASS] {name}")
        else:
            failed += 1
            print(f"[FAIL] {name}")

    # 1. Health check status code
    try:
        req = urllib.request.urlopen(f"{BASE_URL}/health")
        data = json.loads(req.read().decode())
        assert_test("Health check status code 200", req.status == 200)
        assert_test("Health check status ok", data.get("status") == "ok")
    except Exception:
        failed += 2

    # 2. Unknown route 404
    try:
        urllib.request.urlopen(f"{BASE_URL}/nonexistent-route")
        assert_test("Unknown route 404", False)
    except urllib.error.HTTPError as e:
        assert_test("Unknown route 404", e.code == 404)
    except Exception:
        assert_test("Unknown route 404", False)

    # 3. Create without title rejected
    try:
        payload = json.dumps({"reporter": {"name": "Test"}, "impact": 1, "urgency": 1}).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/tickets", data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)
        assert_test("Create without title rejected", False)
    except urllib.error.HTTPError as e:
        assert_test("Create without title rejected", e.code in [400, 422])
    except Exception:
        assert_test("Create without title rejected", False)

    # 4. Create valid ticket P1
    ticket_id = None
    try:
        payload = json.dumps({"title": "Test P1", "reporter": {"name": "Alice"}, "impact": 1, "urgency": 1}).encode("utf-8")
        req = urllib.request.Request(f"{BASE_URL}/tickets", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            ticket_id = data.get("id")
            assert_test("Create valid ticket status 201", resp.status == 201)
            assert_test("Priority is P1", data.get("priority") == "P1")
            assert_test("State is new", data.get("state") == "new")
    except Exception:
        failed += 3

    # 5. Get ticket by ID
    if ticket_id:
        try:
            req = urllib.request.urlopen(f"{BASE_URL}/tickets/{ticket_id}")
            data = json.loads(req.read().decode())
            assert_test("Get ticket by ID status 200", req.status == 200)
            assert_test("Get ticket ID matches", data.get("id") == ticket_id)
        except Exception:
            assert_test("Get ticket by ID", False)
    else:
        failed += 2

    # 6. List tickets filter state=new
    try:
        req = urllib.request.urlopen(f"{BASE_URL}/tickets?state=new")
        data = json.loads(req.read().decode())
        assert_test("List tickets state=new returns list", isinstance(data, list))
    except Exception:
        assert_test("List tickets state=new", False)

    # 7. Ack ticket
    if ticket_id:
        try:
            req = urllib.request.Request(f"{BASE_URL}/tickets/{ticket_id}/ack", data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                assert_test("Ack ticket status 200", resp.status == 200)
                assert_test("Ack ticket state acknowledged", data.get("state") == "acknowledged")
        except Exception:
            failed += 2
    else:
            failed += 2

    print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()