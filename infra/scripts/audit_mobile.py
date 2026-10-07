"""Report every advisory; fail on new findings or expired upstream exceptions."""
import datetime
import json
import os
import shutil
import subprocess
from pathlib import Path

baseline = json.loads(Path('docs/security/mobile-advisories.json').read_text())
if datetime.date.today() > datetime.date.fromisoformat(baseline['review_before']):
    raise SystemExit('Mobile dependency exceptions require renewed review.')
npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
if npm is None:
    raise SystemExit('npm is required to audit mobile dependencies.')
result = subprocess.run([npm, 'audit', '--prefix', 'mobile', '--omit=dev', '--json', '--offline=false'], capture_output=True, text=True)
if result.returncode not in (0, 1):
    raise SystemExit('npm audit failed: ' + result.stderr.strip())
report = json.loads(result.stdout)
if 'error' in report:
    raise SystemExit(report['error'])
if 'vulnerabilities' not in report or 'metadata' not in report:
    raise SystemExit('npm audit returned an incomplete report.')
found = {}
for name, vulnerability in report.get('vulnerabilities', {}).items():
    for advisory in vulnerability['via']:
        if isinstance(advisory, dict):
            found[advisory['url']] = advisory['title']
for url, title in sorted(found.items()):
    print(f'{url}: {title}')
new = set(found) - set(baseline['upstream_advisories'])
if new:
    raise SystemExit('Unreviewed mobile dependency advisories: ' + ', '.join(sorted(new)))
print('All findings reported. Remaining exceptions are limited to the documented upstream advisories.')
