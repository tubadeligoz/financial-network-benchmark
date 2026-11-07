"""Download one official BIS projection; local CSV import remains fully offline."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import urllib.request
from datetime import datetime, timezone


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--period', required=True, help='YYYY-Qn')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'\d{4}-Q[1-4]', args.period):
        parser.error('period must be YYYY-Qn')
    out = Path(args.output)
    paths = [out / 'observations.csv', out / 'manifest.json']
    if any(p.exists() for p in paths):
        parser.error('Output files exist; use a new directory.')
    key = 'Q.S.C.G.TO1.A.5J.A..A..N'
    url = ('https://stats.bis.org/api/v2/data/dataflow/BIS/WS_LBS_D_PUB/1.0/'
           f'{key}?startPeriod={args.period}&endPeriod={args.period}&format=csvfile')
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            raw = response.read()
            last_modified = response.headers.get('Last-Modified')
        rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not rows.fieldnames or 'OBS_VALUE' not in rows.fieldnames:
            raise ValueError('Expected BIS SDMX CSV with OBS_VALUE, not an error/HTML response.')
        if next(rows, None) is None:
            raise ValueError('BIS returned no observations.')
    except Exception as exc:
        parser.exit(2, f'Download failed: {exc}. Supply a local BIS CSV/Parquet and manifest instead.\n')
    out.mkdir(parents=True, exist_ok=True)
    paths[0].write_bytes(raw)
    manifest = dict(dataset_id='bis-lbs', source_url=url, source_version='WS_LBS_D_PUB/1.0',
        accessed_at=datetime.now(timezone.utc).isoformat(), data_kind='observed_aggregate',
        sha256=hashlib.sha256(raw).hexdigest(), upstream_last_modified=last_modified,
        terms_url='https://data.bis.org/help/legal', attribution='Source: BIS locational banking statistics')
    paths[1].write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Saved {len(raw)} bytes; SHA256={manifest["sha256"]}; {out}')


if __name__ == '__main__':
    main()
