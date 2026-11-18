"""Métricas calculadas de las muestras reales; P95 por rango más cercano."""
import argparse
import csv
import json
import math
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('jtl', type=Path)
p.add_argument('--users', type=int, required=True)
a = p.parse_args()
with a.jtl.open(encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
if not rows:
    raise SystemExit('JMeter no produjo muestras')
elapsed = sorted(int(r['elapsed']) for r in rows)
start = min(int(r['timeStamp']) for r in rows)
end = max(int(r['timeStamp']) + int(r['elapsed']) for r in rows)
summary = dict(stack='Go', users=a.users, requests=len(rows),
               average_ms=round(sum(elapsed)/len(rows), 2),
               p95_ms=elapsed[math.ceil(len(rows)*.95)-1],
               throughput_rps=round(len(rows)/((end-start)/1000), 2),
               error_pct=round(100*sum(r['success'].lower() != 'true' for r in rows)/len(rows), 3),
               measured_seconds=round((end-start)/1000, 3))
a.jtl.with_name('summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
with a.jtl.with_name('summary.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=summary)
    w.writeheader()
    w.writerow(summary)
print(json.dumps(summary, indent=2))
