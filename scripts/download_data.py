"""Download a bounded prefix of public, anonymized NBER bargaining records."""
from pathlib import Path
import urllib.request
import hashlib
import json
import time
import zlib

ROOT = Path(__file__).resolve().parent.parent/'data'/'raw'
ROOT.mkdir(parents=True,exist_ok=True)
URL = 'https://back.nber.org/appendix/w24306/bargaining/anon_bo_threads.csv.gz'
LIMIT = 64 * 1024 * 1024
EXPECTED_SHA256 = 'c68403e3759c653ce5a1c5598a71b58d0d6cee97de3d0205635a7dd7fff25285'
archive = ROOT / 'ebay_threads_prefix.gz.part'
request = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0', 'Range': f'bytes=0-{LIMIT-1}'})
start = time.time()
digest = hashlib.sha256()
with urllib.request.urlopen(request, timeout=45) as response:
    headers = {'status': response.status, 'content_range': response.headers.get('Content-Range'), 'content_length': response.headers.get('Content-Length'), 'last_modified': response.headers.get('Last-Modified')}
    with archive.open('wb') as out:
        total = 0
        while total < LIMIT:
            block = response.read(min(1024*1024, LIMIT-total))
            if not block:
                break
            out.write(block)
            digest.update(block)
            total += len(block)
            if total % (16*1024*1024) == 0:
                print(f'Downloaded {total//(1024*1024)} MiB in {time.time()-start:.1f}s', flush=True)
assert total == LIMIT, 'Source response did not provide the requested prefix'
assert digest.hexdigest() == EXPECTED_SHA256, 'Source prefix changed; do not treat the rebuilt sample as equivalent'
decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
csv_path = ROOT / 'ebay_offers_prefix.csv'
pending = b''
with archive.open('rb') as inp, csv_path.open('wb') as out:
    while block := inp.read(1024*1024):
        decoded = pending + decoder.decompress(block)
        last_newline = decoded.rfind(b'\n')
        if last_newline >= 0:
            out.write(decoded[:last_newline+1])
            pending = decoded[last_newline+1:]
        else:
            pending = decoded
manifest = {'source_url': URL, 'headers': headers, 'compressed_bytes': total, 'sha256': digest.hexdigest(), 'decoded_bytes': csv_path.stat().st_size, 'discarded_partial_line_bytes': len(pending), 'elapsed_seconds': round(time.time()-start,2), 'sampling': 'Contiguous file prefix; nonrandom. Exclude the last seller and any incomplete histories before analysis.'}
(ROOT / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest, indent=2))
