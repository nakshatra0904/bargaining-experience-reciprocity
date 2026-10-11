"""Empirical bargaining pilot. Design record: docs/pre_analysis_plan.md.

Uses actual public NBER records, never synthetic observations. See README for
prefix sampling and the selection into observed counteroffers.
"""
from pathlib import Path
import argparse, json, hashlib
REPO = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--raw-directory', type=Path, default=REPO/'data/raw')
parser.add_argument('--output-directory', type=Path, default=REPO/'data/processed')
args = parser.parse_args()
ROOT = args.raw_directory
import numpy as np
import pandas as pd

OUT = args.output_directory
OUT.mkdir(parents=True,exist_ok=True)
flow = []
def mark(label, data):
    row = {'step':label, 'rows':len(data),
           'threads':int(data.anon_thread_id.nunique()),
           'sellers':int(data.anon_slr_id.nunique())}
    flow.append(row)
    print(json.dumps(row), flush=True)

cols = ['anon_item_id','anon_thread_id','anon_byr_id','anon_slr_id',
        'offr_type_id','status_id','offr_price','src_cre_date',
        'slr_hist','byr_hist','any_mssg']
d = pd.read_csv(ROOT/'ebay_offers_prefix.csv', usecols=cols)
mark('Raw prefix',d)
last_seller = int(d.anon_slr_id.iloc[-1])
d = d[d.anon_slr_id.ne(last_seller)].copy()
mark('Drop potentially truncated last seller',d)
# Some source rows repeat byte-for-byte. Retain one identical record. Threads
# with conflicting records at an identical time are excluded below.
duplicates = int(d.duplicated().sum())
d = d.drop_duplicates()
mark('Deduplicate identical analysis-field records',d)
d['timestamp'] = pd.to_datetime(d.src_cre_date,format='%d%b%Y %H:%M:%S',errors='coerce')
assert d.timestamp.notna().all(), 'Unexpected timestamp format'
d = d.sort_values(['anon_thread_id','timestamp'],kind='stable')
g = d.groupby('anon_thread_id',sort=False)
d['round'] = g.cumcount()+1
d['length'] = g.offr_type_id.transform('size')
expected = np.where(d['round'].eq(1),0,np.where(d['round']%2==0,2,1))
row_bad = (d.offr_type_id.ne(expected) | ~d.offr_price.gt(0) |
           d.status_id.isin([6,9]) | d.length.gt(6) |
           (d['round'].lt(d.length) & d.status_id.ne(7)) |
           d.duplicated(['anon_thread_id','timestamp'],keep=False))
bad_threads = set(d.loc[row_bad,'anon_thread_id'])
for c in ['anon_item_id','anon_byr_id','anon_slr_id']:
    bad_threads.update(g[c].nunique().loc[lambda x:x.ne(1)].index.tolist())
d = d[~d.anon_thread_id.isin(bad_threads)].copy()
mark('Strict alternating human offer histories',d)
initial = d[d['round'].eq(1)].set_index('anon_thread_id')
initial = initial[initial.slr_hist.notna() & initial.byr_hist.notna() &
                  initial.slr_hist.ge(0) & initial.byr_hist.ge(0)]
d = d[d.anon_thread_id.isin(initial.index)].copy()
mark('Observed initial experience for both parties',d)
p = d.pivot(index='anon_thread_id',columns='round',values='offr_price')
st = d.pivot(index='anon_thread_id',columns='round',values='status_id')
# Require every observable interior concession to stay between preceding offers.
valid = pd.Series(True,index=p.index)
for t in range(3,7):
    if t not in p: continue
    denom = p[t-1]-p[t-2]
    gam = (p[t]-p[t-2])/denom
    valid &= p[t].isna() | (denom.ne(0) & gam.between(-1e-10,1+1e-10))
p = p[valid]
d = d[d.anon_thread_id.isin(p.index)].copy()
mark('Every observed interior concession bounded in [0,1]',d)
msg = d.groupby('anon_thread_id').any_mssg.max().fillna(0)
z = initial.loc[p.index,['anon_item_id','anon_byr_id','anon_slr_id','slr_hist','byr_hist','timestamp']].copy()
for t in range(1,7):
    if t in p: z[f'p{t}'] = p[t]
z['message'] = msg
z['month'] = z.timestamp.dt.strftime('%Y-%m')
z['gamma_buyer'] = (z.p3-z.p1)/(z.p2-z.p1)
z['gamma_seller'] = (z.p2-z.p4)/(z.p2-z.p3)
z['gap_before'] = (z.p2-z.p1)/z.p2
z['buyer_abs'] = (z.p3-z.p1)/z.p2
z['seller_abs'] = (z.p2-z.p4)/z.p2
z['round3_status'] = st[3]
z['split'] = z.anon_slr_id.map(lambda i:'discovery' if int(hashlib.sha256(str(int(i)).encode()).hexdigest()[:8],16)%2==0 else 'validation')
z['experience_group'] = np.select([z.slr_hist.lt(10), z.slr_hist.lt(100)],['0-9','10-99'],default='100+')
incoming = z[z.p3.notna() & z.gamma_buyer.between(0,1) & z.gap_before.gt(0)].copy()
main = incoming[incoming.p4.notna() & incoming.gamma_seller.between(0,1) & np.isfinite(incoming.gamma_seller)].copy()
main.index.name='anon_thread_id'
incoming.index.name='anon_thread_id'
main.reset_index().to_csv(OUT/'bargaining_analysis_sample.csv',index=False,float_format='%.8g')
incoming.reset_index().to_csv(OUT/'incoming_buyer_offers.csv.gz',index=False,float_format='%.8g',compression='gzip')

meta = {'raw_rows':flow[0]['rows'],'raw_threads':flow[0]['threads'],
        'raw_sellers':flow[0]['sellers'],'last_seller_dropped':last_seller,
        'identical_records_removed':duplicates,'main_threads':len(main),
        'main_sellers':int(main.anon_slr_id.nunique()),
        'incoming_round3':len(incoming),'date_min':str(d.timestamp.min()),
        'date_max':str(d.timestamp.max()),
        'main_date_min':str(main.timestamp.min()),'main_date_max':str(main.timestamp.max()),
        'experience_summary':main.groupby('experience_group').agg(n=('p4','size'),
          sellers=('anon_slr_id','nunique'),buyer_gamma=('gamma_buyer','mean'),
          seller_gamma=('gamma_seller','mean')).reset_index().to_dict('records')}
meta['sample_flow']=flow
meta['source_manifest']=json.loads((ROOT/'download_manifest.json').read_text())
(OUT/'sampling_metadata.json').write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2),flush=True)

