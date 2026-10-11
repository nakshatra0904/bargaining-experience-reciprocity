# Bargaining experience and reciprocity

I investigate whether bargaining experience changes how strongly sellers respond
to a buyer's concession. I use actual eBay Best Offer negotiations to separate
average concession levels from concession-response slopes at a fixed stage.

Start with **[my complete project report](report/project_report.pdf)**. I include
all result tables, four figures, theoretical derivations, references, the proposed
extension and its limitations in that single report.

## What I found

- I estimate a primary experience interaction of 0.0127 (seller-clustered
  SE 0.0587, p=0.829; 27,016 threads). I do not find convincing evidence that
  experienced sellers respond less strongly to buyers' concessions.
- I find a positive common-slope benchmark under remaining-gap fractions (0.090)
  and a negative slope under price movements divided by a common price (-0.097).
  I label the seller-split measurement follow-up as exploratory.
- I propose an experience-response extension that distinguishes concession
  levels from response slopes. Alternative measures already appear in the
  published appendix; I do not claim verified global novelty or causality.

I analyze 30,419 four-offer threads from 4,520 sellers in June 2012-December
2013. I use a nonrandom contiguous prefix. Experience is observational, and
the next seller counteroffer is observed only for continuing negotiations.

## Repository layout

```text
report/project_report.pdf    Complete report, including all four figures
report/project_report.tex    Standalone LaTeX with graphs and references embedded
results/results.json        Single consolidated numerical results file
data/processed/             Analysis and selection samples
data/source/codebook.xlsx    Original source variable definitions
src/bargaining_analysis.py   Shared regression implementation
scripts/                    Reproduction, source preparation and report build
docs/                       Design notes, data provenance, dictionary and checks
.github/workflows/           Numerical reproduction and LaTeX compilation
```

## Reproduce my analysis

I use Python 3.12 and the versions pinned in `requirements.txt`. Run these
commands from the repository root:

```bash
python -m venv .venv
# Activate .venv with the appropriate command for the operating system.
python -m pip install -r requirements.txt
python scripts/run_analysis.py --output build/results.json
python scripts/verify_results.py --candidate build/results.json
python scripts/build_report.py --results results/results.json
```

I consolidate numerical outputs into one JSON file. The verifier compares
re-estimated results with my committed reference, checks sample counts and
checks that the two seller samples do not overlap. The report builder regenerates
the standalone LaTeX source. Persistent report edits belong in its template.

## Compile my report

I compiled the included PDF with hosted pdfLaTeX at [TeXLive.net](https://texlive.net/).
The source can also be compiled in Overleaf or with an existing TeX Live setup.
No separate figure or bibliography files are required.

```bash
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/project_report.tex
pdflatex -interaction=nonstopmode -halt-on-error -output-directory=report report/project_report.tex
```

The source uses standard packages including PGFPlots/TikZ, booktabs, longtable,
geometry, placeins and hyperref. I include a GitHub Actions workflow to rerun
the numerical checks and compile the report.

## Rebuild my sample from the public archive

```bash
python scripts/download_data.py
python scripts/prepare_data.py
python scripts/run_analysis.py --output build/results.json
```

I exclude the raw 64 MiB download and decompressed file from Git. The downloader
checks the original prefix checksum. I verified that the cleaning script rebuilds
the analysis CSV and uncompressed selection sample exactly. A regenerated gzip
file may have different header timestamps; file hashes in the verifier refer to
the exact distributed exports. I use eight significant digits in exported
fields and an absolute numerical verification tolerance of 0.000001.

## Data, license and citation

I document the [data provenance](docs/DATA_PROVENANCE.md),
[variable definitions](docs/DATA_DICTIONARY.md) and [validation](docs/VALIDATION.md).
My analysis builds on [Backus et al. (2020)](https://doi.org/10.1093/qje/qjaa003)
and its [public archive](https://back.nber.org/appendix/w24306/bargaining/).
The MIT license covers my project code and report text, not the third-party data
or source codebook. Bibliographic entries are in `CITATION.bib`.

**Author:** [nakshatra0904](https://github.com/nakshatra0904).
I retain the null primary result and label the measurement discrepancy as
exploratory. This pilot does not establish causality or publication-level novelty.
