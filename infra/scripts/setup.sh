#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
python3 - <<'PYSETUP'
from pathlib import Path
import secrets
p = Path('.env')
if p.exists():
    print('.env already exists; values preserved.')
else:
    source = Path('.env.example').read_text()
    source = source.replace('DJANGO_SECRET_KEY=change-me-generate-with-python-secrets-token-hex-50', 'DJANGO_SECRET_KEY=' + secrets.token_hex(50))
    source = source.replace('TICKET_SIGNING_KEY=change-me-generate-with-python-secrets-token-hex-50', 'TICKET_SIGNING_KEY=' + secrets.token_hex(50))
    p.write_text(source)
    p.chmod(0o600)
    print('Created local .env with independent random signing keys.')
PYSETUP
