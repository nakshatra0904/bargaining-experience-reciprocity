"""Re-estimate the pilot and consolidate numerical outputs into one JSON file."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t as tdist
from src.bargaining_analysis import fit_model


def analyze(output):
    reference = json.loads((ROOT / 'results/results.json').read_text(encoding='utf-8'))
    main = pd.read_csv(ROOT / 'data/processed/bargaining_analysis_sample.csv').set_index('anon_thread_id')
    incoming = pd.read_csv(ROOT / 'data/processed/incoming_buyer_offers.csv.gz').set_index('anon_thread_id')
    assert main.index.is_unique and incoming.index.is_unique
    discovery = set(main.loc[main.split.eq('discovery'), 'anon_slr_id'])
    validation = set(main.loc[main.split.eq('validation'), 'anon_slr_id'])
    assert not discovery.intersection(validation)
    assert main.index.isin(incoming.index).all()
    actual_split = main.anon_slr_id.map(lambda i: 'discovery' if int(hashlib.sha256(str(int(i)).encode()).hexdigest()[:8], 16) % 2 == 0 else 'validation')
    assert actual_split.eq(main.split).all()
    assert np.allclose(main.gamma_buyer, (main.p3-main.p1)/(main.p2-main.p1), atol=1e-7, rtol=1e-7)
    assert np.allclose(main.gamma_seller, (main.p2-main.p4)/(main.p2-main.p3), atol=1e-7, rtol=1e-7)
    assert main.gamma_buyer.between(0, 1).all() and main.gamma_seller.between(0, 1).all()

    specifications = [
        ('Primary: all', main, {}),
        ('Primary: discovery sellers', main[main.split.eq('discovery')], {}),
        ('Primary: validation sellers', main[main.split.eq('validation')], {}),
        ('Seller fixed effects', main, {'fe': True}),
        ('50+ threshold', main, {'high': 50}),
        ('250+ threshold', main, {'high': 250}),
        ('No messages', main[main.message.eq(0)], {}),
        ('Price $1-$1000', main[main.p2.between(1, 1000)], {}),
        ('Exclude midpoint and zero concessions', main[~np.isclose(main.gamma_buyer, .5) & ~np.isclose(main.gamma_seller, .5) & main.gamma_buyer.gt(0) & main.gamma_seller.gt(0)], {}),
        ('Equal weight per seller', main, {'equal_seller': True}),
        ('Both concessions scaled by seller first price', main, {'absolute': True}),
    ]
    primary, coefficients = [], []
    for label, data, options in specifications:
        record, coefs = fit_model(label, data, **options)
        primary.append(record)
        coefficients.extend(coefs)
        print(f"{label}: N={record['n']:,}, interaction={record['slope_difference_estimate']:.6f}", flush=True)

    measurement = []
    for split in ['all', 'discovery', 'validation']:
        z = (main if split == 'all' else main[main.split.eq(split)]).copy()
        z['buyer_own_price_pct'] = (z.p3-z.p1)/z.p1
        for measure, exposure, outcome in [
            ('Remaining-gap fractions', 'gamma_buyer', 'gamma_seller'),
            ('Price movements / S2', 'buyer_abs', 'seller_abs'),
            ('Own preceding-price percentages', 'buyer_own_price_pct', 'seller_abs'),
        ]:
            x = pd.DataFrame({'const': 1., 'buyer_concession': z[exposure],
                 'log_seller_experience': np.log1p(z.slr_hist),
                 'log_buyer_experience': np.log1p(z.byr_hist),
                 'log_initial_seller_price': np.log(z.p2), 'gap_before': z.gap_before}, index=z.index)
            x = pd.concat([x, pd.get_dummies(z.month, prefix='month', drop_first=True, dtype=float)], axis=1)
            m = sm.OLS(z[outcome], x).fit(cov_type='cluster', cov_kwds={'groups': z.anon_slr_id}, use_t=True)
            b, se = float(m.params.buyer_concession), float(m.bse.buyer_concession)
            g = int(z.anon_slr_id.nunique())
            crit = float(tdist.ppf(.975, g-1))
            measurement.append({'sample': split, 'measure': measure, 'n': len(z), 'sellers': g,
                 'slope': b, 'se': se, 'ci_low': b-crit*se, 'ci_high': b+crit*se,
                 'p': float(m.pvalues.buyer_concession)})

    exploratory = [fit_model('Exploratory common-price: '+split,
                   main[main.split.eq(split)], absolute=True)[0] for split in ['discovery', 'validation']]
    bins = np.arange(0, 1.000001, .1)
    for z in [main, incoming]:
        z['buyer_concession_bin'] = pd.cut(z.gamma_buyer, bins=bins, include_lowest=True, labels=False)
    raw = main.groupby(['experience_group', 'buyer_concession_bin']).agg(
        buyer_concession=('gamma_buyer', 'mean'), seller_concession=('gamma_seller', 'mean'),
        n=('gamma_seller', 'size')).reset_index()
    incoming['accepted'] = incoming.round3_status.eq(1).astype(float)
    incoming['countered'] = incoming.round3_status.eq(7).astype(float)
    selection = incoming.groupby(['experience_group', 'buyer_concession_bin']).agg(
        buyer_concession=('gamma_buyer', 'mean'), acceptance=('accepted', 'mean'),
        counteroffer=('countered', 'mean'), n=('accepted', 'size')).reset_index()
    descriptives = []
    for group, z in main.groupby('experience_group'):
        descriptives.append({'experience_group': group, 'n': len(z), 'sellers': int(z.anon_slr_id.nunique()),
            'zero_seller_concession': float(np.isclose(z.gamma_seller, 0).mean()),
            'midpoint_seller_concession': float(np.isclose(z.gamma_seller, .5).mean()),
            'seller_concession_mean': float(z.gamma_seller.mean()),
            'buyer_concession_mean': float(z.gamma_buyer.mean()), 'median_initial_price': float(z.p2.median())})
    # Archive-only metadata cannot be reconstructed from the cleaned samples.
    # Preserve and clearly identify its provenance; every empirical table is refit.
    reference.update(primary_models=primary, coefficients=coefficients,
        measurement_models=measurement, exploratory_group_models=exploratory,
        descriptives=descriptives, binned_concessions=raw.to_dict('records'),
        response_selection=selection.to_dict('records'))
    reference['data_hashes'] = {name: hashlib.sha256((ROOT/'data/processed'/name).read_bytes()).hexdigest()
        for name in ['bargaining_analysis_sample.csv', 'incoming_buyer_offers.csv.gz']}
    reference['reproduction_audit'] = {'unique_threads': True, 'disjoint_seller_halves': True,
        'hash_split_recomputed': True, 'gap_concessions_recalculated': True,
        'archive_metadata_source': 'Committed sampling/source metadata; optional raw-data pipeline independently reconstructs it',
        'versions': {'numpy': np.__version__, 'pandas': pd.__version__, 'statsmodels': sm.__version__}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(reference, indent=2, allow_nan=False), encoding='utf-8')
    print(f'Wrote all numerical outputs to {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/results.json')
    analyze(parser.parse_args().output)
