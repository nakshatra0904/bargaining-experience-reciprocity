# Frozen pilot analysis plan

I recorded this internal design before inspecting the pilot outcomes. I revised
the presentation into first person on 11 October 2026 without changing the
original hypothesis, thresholds, sample restrictions or planned checks.

Question: Does prior bargaining experience moderate reciprocal concession-making in eBay Best Offer negotiations?

Motivation: Backus et al. (QJE 2020) document reciprocal gradualism and separately relate experience to concession levels. This pilot extends that framing to the slope of the response to an opponent's concession. Round-specific reciprocity is already studied, so round heterogeneity alone is not claimed as new.

Hypothesis before inspecting outcomes: Greater own experience is associated with weaker reciprocal concession-making, conditional on continuing with a counteroffer. No claim that experience is randomly assigned or that its effect is causal.

Data: Bounded 64 MiB prefix of the public NBER anonymized offer file. It is a convenience sample, not random or nationally representative. Drop the last seller block (potentially truncated), ambiguous/duplicate rows, histories that are not strictly alternating, automatic accept/reject histories, non-positive prices, and equal preceding offers. Initial experience is taken only from the initial buyer offer and carried forward. I do not use the misleading codebook wording to treat response_time as a duration: validate its timestamp semantics separately.

Primary sample: Human-only threads with a verified initial buyer offer followed by alternating seller/buyer offers. Main transitions are buyer counteroffer 2 to seller counteroffer 2 (observable gamma at rounds 3 and 4, with round 0 being the listing). This is a fixed-stage analysis avoiding mixing proposer roles and horizons. Gamma lies in [0,1]. Listing prices are not needed because both concessions refer to the four observed bargaining offers.

Primary exposure/outcome: Opponent's gamma at round 3 and own gamma at round 4. Seller experience categories 0-9 prior threads vs 100+; retain intermediate category for descriptive displays. Model gamma4 on gamma3, seller experience group and interactions, log(1+buyer experience), log first seller counteroffer, relative price gap immediately before the buyer concession, and month effects. Standard errors clustered by seller. Also estimate seller fixed effects interaction model so experience-level slope differences are not just differences in average seller generosity.

Validation: Deterministic seller-ID hash split (50/50) into discovery and validation, fixed before fitting. Report primary interaction on both halves, plus all sellers for precision. No outcome-based searching for a significant cutoff.

Robustness: 50+ vs 0-9, 250+ vs 0-9, drop messages, restrict price to $1-$1000, exclude exact prior midpoint or zero-concession offers, equal seller weights, alternate absolute price changes normalized by first seller counteroffer, and fit seller fixed effects. Report disagreements and null results.

Secondary: Plot acceptance of incoming buyer round-3 offers vs concession and experience. This helps describe selection into round-4 counteroffers; it is not a solution to selection bias. Do not infer unconditional reciprocity from selected continuers.

Novelty status: Candidate original interaction/validation analysis within this pilot; global novelty not established by a targeted literature search. It is an exploratory project, not a publication-ready causal result.
