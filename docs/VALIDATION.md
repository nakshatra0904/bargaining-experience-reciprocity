# Validation of the delivered package

- I executed all 22 regressions from the supplied processed data: 11 planned
  interaction specifications, 9 measurement comparisons and 2 exploratory
  split-sample interactions.
- I verified 951 comparisons at an absolute tolerance of
  0.000001. Regression/descriptive outputs differed from the original full-
  precision analysis by at most 0.00000001793.
- I checked thread uniqueness, seller-half separation, the hashed split and
  concession arithmetic. All four figures use the consolidated results file.
- I ran the source-cleaning script on the downloaded
  public prefix and rebuilt the analysis CSV byte for byte and the selection
  sample with identical uncompressed contents. Raw source metadata were also
  reproduced. A fresh gzip export can have a different timestamp in its header;
  the verifier's file hashes refer to the exact distributed exports.
- All seven Python source files passed syntax checks.
- I compiled the self-contained report with hosted pdfLaTeX at TeXLive.net. I rendered the
  PDF and visually inspected every page. I checked the four figure captions and
  cross-references and corrected a clipped figure before publication.
- I include a GitHub Actions workflow for numerical reproduction and report
  compilation. Its live run status is available on the repository Actions page.

The verification concerns reproduction and presentation. It does not establish
causality, representativeness, or global novelty.
