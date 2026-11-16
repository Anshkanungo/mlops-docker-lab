"""The container's entry point: what it writes, and that it refuses bad data."""
import json
from pathlib import Path

from src import classify

SNAPSHOT = Path(__file__).resolve().parent.parent / 'data' / 'products.json'


def test_writes_three_files_with_full_agreement(tmp_path):
    assert classify.main(['--input', str(SNAPSHOT), '--output', str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        'diet_metrics.json', 'products_classified.json', 'validation.json']
    metrics = json.loads((tmp_path / 'diet_metrics.json').read_text())
    assert metrics['products'] == 17
    assert metrics['agreement'] == 1.0
    assert metrics['mismatches'] == []
    # v1 said 6 / 6 / 5: Oscar Mayer Original Bacon was counted as vegan
    assert metrics['per_diet'] == {'non-vegetarian': 7, 'vegan': 5, 'vegetarian': 5}


def test_bad_record_stops_before_classifying(tmp_path):
    snapshot = json.loads(SNAPSHOT.read_text())
    snapshot['products'][0]['barcode'] = 'not-a-barcode'
    snapshot['products'][1]['evidence']['allergens'] = 'milk'      # should be a list
    snapshot['products'].append(snapshot['products'][2])            # duplicate barcode
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps(snapshot))
    out = tmp_path / 'out'

    assert classify.main(['--input', str(bad), '--output', str(out)]) == 1
    report = json.loads((out / 'validation.json').read_text())
    assert (report['invalid'], report['duplicates']) == (2, 1)
    assert not (out / 'products_classified.json').exists()
