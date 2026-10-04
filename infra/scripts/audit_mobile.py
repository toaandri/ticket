"""Report every advisory; fail on new findings or expired upstream exceptions."""
import datetime
import json
import subprocess
from pathlib import Path

baseline = json.loads(Path('docs/security/mobile-advisories.json').read_text())
if datetime.date.today() > datetime.date.fromisoformat(baseline['review_before']):
    raise SystemExit('Mobile dependency exceptions require renewed review.')
result = subprocess.run(['npm', 'audit', '--prefix', 'mobile', '--omit=dev', '--json'], capture_output=True, text=True)
report = json.loads(result.stdout)
if 'error' in report:
    raise SystemExit(report['error'])
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
