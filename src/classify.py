"""Container entry point: validate a product snapshot, run the diet rules, write the results.

    python -m src.classify --input data/products.json --output output

Writes to the output folder (mount it as a volume so the files outlive the container):
- validation.json            record counts; the run stops with exit code 1 if any record is bad
- products_classified.json   each product with its diet, the reason, and the hand-checked label
- diet_metrics.json          products per diet, agreement with the labels, and the mismatches
"""
import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.diet_rules import DIETS, classify

LABELS = set(DIETS) | {None}


def problems(p):
    """Return a list of what is wrong with one product record (empty if it is fine)."""
    found = []
    if not str(p.get('barcode', '')).isdigit():
        found.append('barcode is missing or not digits')
    if not p.get('name'):
        found.append('name is missing')
    if p.get('expected_diet') not in LABELS:
        found.append(f'expected_diet is not one of {list(DIETS)} or null')
    ev = p.get('evidence')
    if not isinstance(ev, dict):
        return found + ['evidence is missing']
    if not isinstance(ev.get('ingredients_text'), str):
        found.append('evidence.ingredients_text is not text')
    for key in ('allergens', 'traces'):
        if not isinstance(ev.get(key), list):
            found.append(f'evidence.{key} is not a list')
    if not isinstance(ev.get('complete'), bool):
        found.append('evidence.complete is not true/false')
    return found


def validate(products):
    """Return (report, errors). `errors` lists one line per bad record or duplicate barcode."""
    errors = [f"{p.get('barcode', f'#{i}')}: " + '; '.join(problems(p))
              for i, p in enumerate(products) if problems(p)]
    barcodes = [p.get('barcode') for p in products]
    duplicates = sorted({b for b in barcodes if barcodes.count(b) > 1})
    errors += [f'duplicate barcode: {b}' for b in duplicates]
    report = dict(products=len(products), invalid=len(errors) - len(duplicates), duplicates=len(duplicates),
                  complete_evidence=sum(p.get('evidence', {}).get('complete') is True for p in products))
    return report, errors


def run(products):
    """Classify every product. Returns (rows, metrics)."""
    rows = []
    for p in products:
        diet, reason = classify(p['evidence'], p['name'])
        rows.append(dict(barcode=p['barcode'], name=p['name'], brand=p.get('brand'),
                         diet=diet, reason=reason, expected_diet=p.get('expected_diet')))
    labeled = [r for r in rows if r['expected_diet']]
    mismatches = [r for r in labeled if r['diet'] != r['expected_diet']]
    metrics = dict(
        rules_version='v2',
        products=len(rows),
        per_diet=dict(sorted(Counter(r['diet'] for r in rows).items())),
        labeled=len(labeled),
        agreement=round(1 - len(mismatches) / len(labeled), 4) if labeled else None,
        mismatches=[dict(barcode=r['barcode'], name=r['name'], rules=r['diet'], expected=r['expected_diet'])
                    for r in mismatches],
    )
    return rows, metrics


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--input', type=Path, default=Path('data/products.json'))
    parser.add_argument('--output', type=Path, default=Path('output'))
    args = parser.parse_args(argv)

    snapshot = json.loads(args.input.read_text())
    products = snapshot['products']
    args.output.mkdir(parents=True, exist_ok=True)

    report, errors = validate(products)
    write_json(args.output / 'validation.json', report)
    print(f"Validated {report['products']} products from {args.input}: "
          f"{report['invalid']} invalid, {report['duplicates']} duplicate barcodes")
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        print('Validation failed; nothing classified', file=sys.stderr)
        return 1

    rows, metrics = run(products)
    write_json(args.output / 'products_classified.json',
               dict(source=snapshot.get('source'), retrieved=snapshot.get('retrieved'),
                    classified_at=datetime.now(timezone.utc).isoformat(timespec='seconds'), products=rows))
    write_json(args.output / 'diet_metrics.json', metrics)

    width = max(len(r['name']) for r in rows)
    for r in rows:
        print(f"  {r['name'][:width]:<{width}}  {r['diet']:<15} {r['reason']}")
    print(f"Per diet: {metrics['per_diet']}; agreement with labels: {metrics['agreement']} "
          f"({metrics['labeled']} labelled, {len(metrics['mismatches'])} mismatches)")
    print(f'Wrote 3 files to {args.output}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
