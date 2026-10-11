# Data provenance

Source: https://back.nber.org/appendix/w24306/bargaining/anon_bo_threads.csv.gz
Codebook: https://back.nber.org/appendix/w24306/bargaining/Codebook.xlsx
Original study: Backus et al. (2020), DOI 10.1093/qje/qjaa003.

I derive the supplied processed data from actual anonymized records in a
nonrandom 64 MiB prefix of the public research archive. There are no inDrive
observations and no simulated observations in the regressions. Sampling,
source checksum and filters are recorded in results/results.json and the report.

The source codebook says experience measures previous threads; the paper's
Table I discussion includes the current thread. I use the raw experience count unchanged. Labels and thresholds refer to the recorded count.

The MIT license does not cover the source data or codebook. Source access and
reuse remain governed by the source providers' terms; I do not
assert a new redistribution license for those materials.

The pre-analysis note is an internal design record, not an externally registered
pre-analysis plan. Its reference to the buyer's second offer is the first buyer
counteroffer, B3, in the report. The own-price percentage diagnostic was added
after finding the published appendix's alternative definition.

## Export precision and graph bins

The distributed cleaned sample uses eight significant digits. I recompute all reported
regressions and graph summaries after reloading that sample. This preserves numerical reproducibility. A small number
of concessions close to exact bin boundaries move between adjacent bins compared
with the initial full-precision raw-data plots; no regressions or substantive
conclusions change. The maximum difference from the original regression and
descriptive outputs is 1.7928520557042305e-08.
