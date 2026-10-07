"""Create local signing keys once; usable from Windows, macOS and Linux."""

import os
import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    target = root / ".env"
    if target.exists():
        print(".env already exists; values preserved.")
        return
    source = (root / ".env.example").read_text(encoding="utf-8")
    for name in ("DJANGO_SECRET_KEY", "TICKET_SIGNING_KEY"):
        source = source.replace(f"{name}=change-me-generate-with-python-secrets-token-hex-50", f"{name}={secrets.token_hex(50)}")
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(".env already exists; values preserved.")
        return
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(source)
    print("Created local .env with independent random signing keys.")


if __name__ == "__main__":
    main()
