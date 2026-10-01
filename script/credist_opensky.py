import os, requests
from dotenv import load_dotenv
from opensky_api import TokenManager

load_dotenv()
tm = TokenManager(os.getenv("CLIENT_ID"), os.getenv("CLIENT_SECRET"))

r = requests.get(
    "https://opensky-network.org/api/flights/departure",
    params={"airport": "LSZH", "begin": 1790000000, "end": 1790003600},  # 1 h
    headers=tm.auth_headers(),
    timeout=15,
)
print(r.status_code)
print(r.headers.get("X-Rate-Limit-Remaining"))
print(r.headers.get("X-Rate-Limit-Retry-After-Seconds"))