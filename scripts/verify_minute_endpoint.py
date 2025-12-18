
import requests
import json

# Adjust code to whatever is current (from previous verification output)
# We saw mo2512C4900 in the previous valid output
CODE = "mo2512C4900" 
URL = f"http://localhost:8080/api/options/{CODE}/minute"

print(f"Verifying {URL}...")
try:
    resp = requests.get(URL)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        print("Success! Response:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
    else:
        print(f"Failed with status {resp.status_code}")
        print(resp.text)
except Exception as e:
    print(f"Error: {e}")
