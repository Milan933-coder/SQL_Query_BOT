import requests
import json

url = "https://milan933-coder--nl-sql-vllm-web-dev.modal.run/query"
data = {"question": "Show all customers from USA"}

try:
    response = requests.post(url, json=data)
    # This prints the JSON response from your Modal deployment
    print(json.dumps(response.json(), indent=4))
except Exception as e:
    print(f"Error: {e}")