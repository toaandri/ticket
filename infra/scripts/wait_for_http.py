"""Fail clearly if development services do not become ready within 45 seconds."""
import sys
import time
import urllib.request
from urllib.error import URLError

for url in sys.argv[1:]:
    deadline = time.monotonic() + 45
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    break
        except (URLError, TimeoutError):
            pass
        if time.monotonic() >= deadline:
            raise SystemExit(f"Service did not become ready: {url}")
        time.sleep(0.5)
