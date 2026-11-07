# Benchmarking Graph-Based Bottleneck Detection Methods in Financial Networks

Research draft — structural country-level indicators and separate synthetic distress scenarios. Not a validated forecast of bank failure or liquidity shortages.

## 1. Abstract

This project compares graph-based critical-node indicators on published BIS country claims and an independent fictional bank model. Directed weighted snapshots preserve source provenance and missing-data limitations. Strength, shortest-path betweenness and PageRank represent different structural questions. Single-pass DebtRank is evaluated only on explicitly synthetic balance sheets. Final validation reran sixty isolated timing/memory trials; numerical tables are generated from completed artifacts. Results support reproducible descriptive comparison, not predictive accuracy or identification of actual liquidity bottlenecks.

## 2. Introduction

The term bottleneck requires an operational definition. High exposure volume, mediation of shortest paths, directed importance and distress amplification are distinct constructs. Financial interpretation therefore precedes computation. A numerical graph alone does not establish bank-level exposure, capital adequacy or transferable payment capacity.

## 3. Research Questions

RQ1: How do structural node rankings differ on the same observed snapshot? RQ2: What are the measured runtime and process-memory costs under a common protocol? RQ3: How do explicit synthetic capital and shock assumptions affect distress? RQ4: Which provenance and validation controls permit results to be traced and rerun?

## 4. Related Work

[Brandes (2001)](https://www.uni-konstanz.de/algo/publications/b-fabc-01.pdf) provides an efficient shortest-path betweenness method. [Brin and Page (1998)](https://snap.stanford.edu/class/cs224w-readings/Brin98Anatomy.pdf) describe link-based importance in a different application domain. [Battiston et al. (2012)](https://doi.org/10.1038/srep00541) introduce DebtRank; [Bardoscia et al. (2015)](https://doi.org/10.1371/journal.pone.0130406) develop a distinct accounting-based propagation variant. These methods do not automatically share a financial objective.

## 5. Dataset Description

The approved BIS LBS projection represents reporting banks in creditor country A and all debtor sectors in country B. It is not a bilateral individual-bank network. Q4 2025 contains 218 nodes and 3094 observed edges; Q3 contains 219 and 3095. Equity and matched bank balance sheets are absent. The independent five-bank, two-period synthetic model supplies explicitly fictional book equity and consistent starting balance sheets. No bank exposures are reconstructed from BIS aggregates. [BIS methodology](https://data.bis.org/topics/LBS); detailed fields and hashes: [datasets](datasets.md).

## 6. Graph Construction Methodology

CSV/Parquet records undergo schema, identity, period, units, duplication and weight validation. Missing/suppressed observations are explicitly reported and never converted to zero. The graph is creditor-to-debtor; original fields and source hashes are retained. Canonical snapshots and read-only execution prevent algorithm-side mutation. [Graph model](graph-model.md).

## 7. Selected Algorithms

Strength sums incoming/outgoing exposure. Directed betweenness uses unweighted hops or a separately declared distance c/exposure. Exposure is not directly treated as distance. PageRank propagates importance along the declared direction; it does not estimate default probability. Synthetic single-pass DebtRank transfers distress in the reverse debtor-to-creditor direction, using capped exposure/equity impact and one transmission per node. Its aggregate additional distress is R=H_final−H_initial. Received node distress and separate seed-impact rankings are distinct outputs. Definitions and parameters: [algorithms](algorithms.md), [advanced model](advanced-financial-analysis.md).

## 8. Experimental Setup

Fresh worker processes, serial trial scheduling, five timing and five separate memory repeats per case, declared warmups, fixed seeds and bounded time/RSS budgets are used. Final runs contain backend source archives and dependency/hardware metadata. Historical Phase 3 scaling experiments remain a separate cohort. [Reproducibility](reproducibility.md).

## 9. Benchmark Metrics

Compute time excludes loading, snapshot copying, ranking and serialization. Sampled RSS includes the process baseline and may miss short peaks; OS high-water marks have a broader lifetime scope. Mean, median, sample standard deviation, minimum, maximum, successful counts and failure statuses are retained. Ranking agreement uses Spearman, top-k overlap and Jaccard under declared tie/universe rules; undefined cases are not filled with zero.

## 10. Experimental Results

The actual final runs completed sixty of sixty measurements. All completed repeated rankings matched their references. The generated [experimental-results tables](experimental-results.md) provide current numerical values, graph hashes and run IDs; [evidence-index.json](evidence-index.json) records the underlying summaries and environments. No missing experiment is represented by an invented table or figure. Historical scaling and ten controlled exact-betweenness timeouts are reported separately in the Phase 3 report.

## 11. Discussion

Algorithm cost can be compared without assuming common score meaning. Agreement does not establish causal financial importance. Country-path interpretation is constrained by asymmetric creditor/debtor institutional scope. Synthetic results demonstrate the implemented model and its sensitivity, not empirical systemic risk. Diagnostic loader/API optimizations preserved checked graph identities and nine score digests; sequential timings remain sensitive to machine load.

## 12. Limitations

No crisis outcome labels, true interbank matrix, capital data for BIS nodes, payment capacities or calibrated loss process are available. No real-bank DebtRank or financial max-flow result is claimed. Hardware/load and short RSS sampling limit performance inference. Older historical runs lack source archives. mypy coverage is gradual; hosted GitHub CI has not been executed without authorized publication. Code licensing remains an owner decision.

## 13. Conclusion

The platform provides traceable descriptive graph experiments with explicit data and model boundaries. It supports academic demonstration and further validation while leaving empirical predictive claims unproven. Future work requires matched bank data, approved financial assumptions, broader independent testing and validated backend-equivalence experiments.

## 14. References

Primary sources are linked in Related Work and Dataset Description. Additional implementation references: [NetworkX](https://networkx.org/documentation/stable/), [igraph API](https://igraph.org/python/versions/latest/api/igraph.GraphBase.html). igraph was researched as an alternative but not substituted or benchmarked; its cutoff is not equivalent to sampled-source k. Direction, normalization, distance, seed and convergence equivalence must be tested before migration.
