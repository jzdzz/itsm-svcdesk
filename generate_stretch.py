# ai-generated: 100% - Stretch 2 rework-class calculation
import urllib.request
import json
import hashlib
import re
from datetime import datetime, timezone

url = "https://api.github.com/repos/swasik/itsm-2026-submissions/issues?state=all&labels=receipted,kind:submission&per_page=100"
print("Pobieranie danych z GitHuba ")

all_issues = []

# Pobieranie danych bezpośrednio przez API HTTP
while url:
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github.v3+json")
    # Publiczne repozytorium nie wymaga autoryzacji do odczytu
    try:
        with urllib.request.urlopen(req) as response:
            page_data = response.read()
            issues = json.loads(page_data.decode('utf-8'))
            all_issues.extend(issues)
            
            link_header = response.getheader('Link')
            url = None
            if link_header:
                links = link_header.split(',')
                for link in links:
                    if 'rel="next"' in link:
                        url = link[link.find('<')+1:link.find('>')]
                        break
    except Exception as e:
        print(f"Błąd sieci: {e}")
        exit(1)

# Formatowanie JSON dokładnie tak, jak robi to narzędzie `gh`
payload_bytes = json.dumps(all_issues, separators=(',', ':')).encode('utf-8')
capture_path = "payload.json"

with open(capture_path, "wb") as f:
    f.write(payload_bytes)

sha256_hash = hashlib.sha256(payload_bytes).hexdigest()

deployments = len(all_issues)
rework_deployments = 0

for issue in all_issues:
    title = issue.get("title", "") or ""
    body = issue.get("body", "") or ""
    if re.search(r'lab\d+/v[2-9]', title) or re.search(r'lab\d+/v[2-9]', body):
        rework_deployments += 1

rate = round(rework_deployments / deployments, 6) if deployments > 0 else 0.0

now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
out = {
    "source": "gh api --paginate \"repos/swasik/itsm-2026-submissions/issues?state=all&labels=receipted,kind:submission&per_page=100\"",
    "captured_at": now,
    "capture_path": capture_path,
    "sha256": sha256_hash,
    "deployments": deployments,
    "rework_deployments": rework_deployments,
    "deployment_rework_rate": rate
}

with open("rework-class.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)

print(f"Gotowe! Znaleziono {deployments} wdrożeń, w tym {rework_deployments} poprawek.")