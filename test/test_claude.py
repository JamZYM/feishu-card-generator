import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")

PROXY = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "http://127.0.0.1:10809"


def test_claude():
    proxies = {"http": PROXY, "https": PROXY}
    print(f"Proxy: {PROXY}")
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print(f"API Key: {API_KEY[:20]}...{API_KEY[-4:]}" if len(API_KEY) > 20 else f"API Key: {API_KEY}")
    print("-" * 50)

    if not API_KEY or API_KEY == "sk-ant-xxxxxxxxxxxxx":
        print("ERROR: Please set your real ANTHROPIC_API_KEY in test/.env")
        sys.exit(1)

    print("Sending request to Claude API...")
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "content-type": "application/json",
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": MODEL,
                "max_tokens": 128,
                "messages": [{"role": "user", "content": "Hello, reply in one short sentence."}],
            },
            proxies=proxies,
            timeout=30,
        )
    except requests.exceptions.ProxyError as e:
        print(f"Proxy error: {e}")
        print("Check if proxy 127.0.0.1:10809 is running.")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        print("Check your network or proxy settings.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("Request timed out after 30s.")
        sys.exit(1)

    print(f"Status: {resp.status_code}")
    data = resp.json()
    if resp.status_code == 200:
        print(f"Model: {data.get('model', '?')}")
        print(f"Response: {data['content'][0]['text'].strip()}")
        print("-" * 50)
        print("SUCCESS: Claude API is available!")
    else:
        print(f"Error: {data}")
        print("-" * 50)
        print("FAIL: Claude API is not available.")


if __name__ == "__main__":
    test_claude()
