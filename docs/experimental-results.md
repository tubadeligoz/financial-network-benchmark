# Experimental Results

Faz 6 gerçek koşuları; tarihsel Faz 3/5 sonuçlarıyla birleştirilmez. Süreler hesaplama sınırıdır; RSS süreç tabanını içerir.

| Experiment / case | n / m | Median ms | Mean ms | SD ms | Peak RSS MiB median | Timing / memory successes |
|---|---:|---:|---:|---:|---:|---:|
| final-synthetic-debtrank-v1 / debtrank-impact | 5 / 5 | 0.3669 | 0.3696 | 0.0149 | 89.797 | 5 / 5 |
| final-synthetic-debtrank-v1 / debtrank-scenario | 5 / 5 | 0.1836 | 0.1831 | 0.0117 | 89.902 | 5 / 5 |

Run `20261107T190955-5aecd7fe`; graph `605bfe5195251491853e5213878e330dcf6c940ab8e7d9a4bdf4eb588088d6b7`.

| final-bis-2025q4-v1 / betweenness-exact | 218 / 3094 | 22.9319 | 22.8785 | 0.2618 | 104.035 | 5 / 5 |
| final-bis-2025q4-v1 / betweenness-inverse-exact | 218 / 3094 | 57.9705 | 57.6348 | 1.2906 | 105.391 | 5 / 5 |
| final-bis-2025q4-v1 / pagerank | 218 / 3094 | 4.3928 | 4.3772 | 0.2574 | 112.832 | 5 / 5 |
| final-bis-2025q4-v1 / strength | 218 / 3094 | 3.5964 | 3.5800 | 0.1336 | 103.309 | 5 / 5 |

Run `20261107T191023-591ad944`; graph `685d173adc6d483df20b4c409409035d79554ef86621553a4d93b4c76673e144`.


## Interpretation

Strength measures exposure volume; betweenness structural shortest-path mediation; PageRank directed importance. DebtRank here measures only explicitly synthetic distress. Runtime comparisons do not establish predictive accuracy or a common financial target. Five repeats and uncontrolled system load do not establish statistical significance.

BIS country edges are published aggregate claims projected to a graph, not reconstructed bank exposures. Missing pairs remain unknown. The separate bank model is handcrafted synthetic data.

Full parameters, source hashes, hardware, dependencies, comparisons and source archive digests are indexed in [evidence-index.json](evidence-index.json). Raw trials remain under each local run directory. Historical scaling and controlled timeouts are separately documented in [phase3-results.md](phase3-results.md); they use the historical code environment.