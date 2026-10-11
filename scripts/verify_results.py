"""Verify reproduced empirical tables against the committed numerical reference."""
from pathlib import Path
import argparse
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', type=Path, default=ROOT/'build/results.json')
parser.add_argument('--reference', type=Path, default=ROOT/'results/results.json')
parser.add_argument('--tolerance', type=float, default=1e-6)
args = parser.parse_args()
reference = json.loads(args.reference.read_text(encoding='utf-8'))
candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
max_difference = 0.
comparisons = 0


def compare(expected, actual, location):
    global max_difference, comparisons
    if isinstance(expected, dict):
        assert set(expected) == set(actual), f'Keys differ at {location}'
        for key in expected:
            compare(expected[key], actual[key], f'{location}.{key}')
    elif isinstance(expected, list):
        assert len(expected) == len(actual), f'Length differs at {location}'
        for i, (a, b) in enumerate(zip(expected, actual)):
            compare(a, b, f'{location}[{i}]')
    elif isinstance(expected, bool) or isinstance(expected, str) or expected is None:
        assert expected == actual, f'Value differs at {location}'
    elif isinstance(expected, int):
        assert expected == actual, f'Count differs at {location}: {expected} != {actual}'
    else:
        difference = abs(expected-actual)
        assert math.isfinite(actual) and difference <= args.tolerance, f'Numerical mismatch at {location}: {difference}'
        max_difference = max(max_difference, difference)
        comparisons += 1


for key in ['primary_models', 'coefficients', 'measurement_models', 'exploratory_group_models',
            'descriptives', 'binned_concessions', 'response_selection']:
    compare(reference[key], candidate[key], key)
for name, digest in reference['data_hashes'].items():
    actual = hashlib.sha256((ROOT/'data/processed'/name).read_bytes()).hexdigest()
    assert actual == digest, f'Committed sample changed: {name}'
    assert candidate['data_hashes'][name] == digest, f'Reproduction used a different sample: {name}'
assert len(candidate['primary_models']) == 11
assert len(candidate['measurement_models']) == 9
assert len(candidate['exploratory_group_models']) == 2
assert candidate['primary_models'][0]['n'] == 27016
assert candidate['primary_models'][0]['sellers'] == 3004
for key in ['unique_threads', 'disjoint_seller_halves', 'hash_split_recomputed', 'gap_concessions_recalculated']:
    assert candidate['reproduction_audit'][key]
print(json.dumps({'passed': True, 'numerical_comparisons': comparisons,
                  'maximum_absolute_difference': max_difference, 'tolerance': args.tolerance}, indent=2))
