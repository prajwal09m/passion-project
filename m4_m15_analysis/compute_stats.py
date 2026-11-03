"""Read-only M4-M15 statistical computation.

Reads repository artifacts only. Writes CSV/JSON/PNGs into
m4_m15_analysis/ (new analysis directory; no app source touched).
"""
import csv
import json
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
BM = os.path.join("model_autopsy", "benchmarks")
rng = np.random.default_rng(20261101)


def boot_mean_ci(x, n_boot=20000, seed=7):
    r = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    bs = r.integers(0, len(x), (n_boot, len(x)))
    m = x[bs].mean(axis=1)
    return float(m.mean()), [float(np.percentile(m, 2.5)),
                             float(np.percentile(m, 97.5))]


def wilson(p_hat, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    d = 1 + z * z / n
    c = p_hat + z * z / (2 * n)
    m = z * math.sqrt(p_hat * (1 - p_hat) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


# ---- ground data (each value verified against artifacts; see provenance) ----
m4_projects = [1.0, 1.0, 1.0, 1.0, 1.0, 0.62, 1.0, 0.94]  # eval manifest
m10_scen = [1.0, 1.0, 0.25, 1.0, 1.0, 1.0, 1.0, 1.0]  # challenge report
live_overall = {  # scorecard.json overall per run
    "M5": 0.55, "M6": 0.62, "M7": 0.61, "M8": 0.62,
    "M9int": 0.62, "M13": 0.63, "M14": 0.63,
}
live_tokens = {  # manifest budget.tokens.total (provider-reported)
    "M5": 28192, "M6": 37429, "M7": 38671, "M8": 29527,
    "M9int": 29818, "M13": 44181, "M14": 30170,
}
live_cost = {  # manifest budget.cost_usd.spent (provider-reported)
    "M5": 0.030836, "M6": 0.053972, "M7": 0.058404, "M8": 0.03394,
    "M9int": 0.035007, "M13": 0.057286, "M14": 0.037252,
}
live_discovery = {"M5": 0.4, "M6": 0.0, "M7": 0.0, "M8": 0.0,
                  "M9int": 0.0, "M13": 0.0, "M14": 0.0}
tests = {"M4": 260, "M5": 277, "M6": 287, "M7": 304, "M8": 346,
         "M9": 408, "M13": 425, "M14": 439, "M15": 459}

stats = {}
m4m, m4ci = boot_mean_ci(m4_projects)
stats["m4_mean"] = {"mean": round(float(np.mean(m4_projects)), 4),
                    "sd": round(float(np.std(m4_projects, ddof=1)), 4),
                    "n": 8, "boot_ci95": [round(v, 4) for v in m4ci]}
m10m, m10ci = boot_mean_ci(m10_scen)
stats["m10_mean"] = {"mean": round(float(np.mean(m10_scen)), 4),
                     "sd": round(float(np.std(m10_scen, ddof=1)), 4),
                     "n": 8, "boot_ci95": [round(v, 4) for v in m10ci]}
# M10 binary discovery (5/8 mechanisms discovered; controls separate)
lo, hi = wilson(5 / 8, 8)
stats["m10_discovery_rate"] = {"k": 5, "n": 8, "rate": 0.625,
                               "wilson_ci95": [round(lo, 4),
                                               round(hi, 4)]}
# Live discovery zero-rate over M6..M14 (6 runs, discovery 0.0 each)
lo0, hi0 = wilson(0.0, 6)
stats["live_discovery_zero_M6_M14"] = {
    "k_zero": 6, "n": 6, "wilson_ci95_zero_rate": [round(lo0, 4),
                                                  round(hi0, 4)],
    "note": "M5 scored 0.4 under a partial-credit dimension; "
            "M6+ use strict 0.0 (no confirmed findings)"}
toks = np.array([live_tokens[k] for k in
                 ["M5", "M6", "M7", "M8", "M9int", "M13", "M14"]],
                dtype=float)
costs = np.array([live_cost[k] for k in
                  ["M5", "M6", "M7", "M8", "M9int", "M13", "M14"]],
                 dtype=float)
stats["live_tokens"] = {"mean": round(float(toks.mean()), 1),
                        "sd": round(float(toks.std(ddof=1)), 1),
                        "min": int(toks.min()), "max": int(toks.max()),
                        "n": 7}
stats["live_cost"] = {"mean": round(float(costs.mean()), 4),
                      "sd": round(float(costs.std(ddof=1)), 4),
                      "min": round(float(costs.min()), 4),
                      "max": round(float(costs.max()), 4), "n": 7}
# Paired check: same project live repeats (turbine M5 vs M9int;
# credit M7 vs M13). Different scorer versions -> descriptive only.
stats["paired_repeats_descriptive"] = {
    "turbine_M5_vs_M9int": {"M5": 0.55, "M9int": 0.62,
                            "delta": 0.07,
                            "note": "different scorer generations; "
                                    "no significance claim"},
    "credit_M7_vs_M13": {"M7": 0.61, "M13": 0.63, "delta": 0.02,
                         "note": "different scorer generations; "
                                 "no significance claim"}}
# Multi-agent: identical values on two DIFFERENT scenarios -> no test
stats["multi_agent"] = {"single": 0.688, "team": 0.773,
                        "delta": 0.085, "pct": 12.4,
                        "note": "n=1 scenario each (b_unit_shift M13, "
                                "c_robustness M14); identical values "
                                "across different scenarios; "
                                "no significance testable"}
# Regression check on live overall (ordinary least squares vs order)
order = np.arange(7)
y = np.array([live_overall[k] for k in
              ["M5", "M6", "M7", "M8", "M9int", "M13", "M14"]])
A = np.vstack([order, np.ones(7)]).T
slope, icept = np.linalg.lstsq(A, y, rcond=None)[0]
stats["live_overall_trend"] = {"slope_per_step": round(float(slope), 4),
                               "M5": 0.55, "M14": 0.63,
                               "abs_gain": 0.08,
                               "note": "different projects/scorers per "
                                       "point; trend is descriptive, "
                                       "not a significance claim"}

with open(os.path.join(OUT, "stats.json"), "w") as f:
    json.dump(stats, f, indent=2)

# ---- CSV: milestone comparison table ----
rows = [
    ("overall_score", {"M4": 0.945, "M5": 0.55, "M6": 0.62, "M7": 0.61,
                       "M8": 0.62, "M9": "n/a-offline-means-see-note",
                       "M10": 0.906, "M11": "n/a-ablation-only",
                       "M12": "n/a-no-eval", "M13": 0.63, "M14": 0.63,
                       "M15": "n/a-no-live"}),
    ("discovery", {"M4": "n/a-verdict-based", "M5": 0.4, "M6": 0.0,
                   "M7": 0.0, "M8": 0.0, "M9": 0.938, "M10": 0.906,
                   "M11": "n/a", "M12": "n/a", "M13": 0.0, "M14": 0.0,
                   "M15": "n/a-no-live"}),
    ("evidence_quality", {"M5": 0.5, "M6": 1.0, "M7": 1.0, "M8": 1.0,
                          "M9": "n/a", "M10": "n/a", "M13": 1.0,
                          "M14": 1.0}),
    ("causal_reasoning", {"M5": "n/a-dim-missing", "M6": 0.5,
                          "M7": 0.5, "M8": "n/a-qual-only",
                          "M9": 0.75, "M13": "n/a-live",
                          "M14": "n/a-live"}),
    ("reasoning", {"M5": 0.6, "M6": 0.6, "M7": 0.6, "M8": 0.6,
                   "M9int": 0.6, "M13": 0.6, "M14": 0.6}),
    ("calibration_dim", {"M5": 0.5, "M6": 1.0, "M7": 1.0, "M8": 1.0,
                         "M9int": 1.0, "M13": 1.0, "M14": 1.0}),
    ("efficiency_dim", {"M5": 0.8, "M6": 0.6, "M7": 0.4, "M8": 0.6,
                        "M9int": 0.6, "M13": 0.8, "M14": 0.8}),
    ("reproducibility_dim", {"M5": 1.0, "M6": 1.0, "M7": 1.0, "M8": 1.0,
                             "M9int": 1.0, "M13": 1.0, "M14": 1.0}),
    ("precision_offline", {"M10": 1.0}),
    ("recall_offline", {"M9": 0.938, "M10": 0.906}),
    ("correct_null_rate", {"M10": 1.0}),
    ("false_positives_live", {"M5": 0, "M6": 0, "M7": 0, "M8": 0,
                              "M9int": 0, "M13": 0, "M14": 0}),
    ("experiments_completed", {"M5": 5, "M6": 6, "M7": 8, "M8": 6,
                               "M9int": 6, "M13": 6, "M14": 6}),
    ("experiment_cap_breaches", {"M5": 0, "M6": 0, "M7": 1, "M8": 0,
                                 "M9int": 0, "M13": 0, "M14": 0}),
    ("hypotheses_generated", {"M5": 3, "M6": 3, "M7": 3, "M8": 3,
                              "M9int": 3, "M13": 2, "M14": 3}),
    ("projects_evaluated", {"M4": 8, "M10": 8, "M13-corpusB": 6,
                            "M14-corpusC": 6, "M15-corpusD": 4}),
    ("offline_tests_passed", tests),
    ("live_tokens_total", live_tokens),
    ("live_cost_usd", live_cost),
    ("team_vs_single", {"M13-team": 0.773, "M13-single": 0.688,
                        "M14-team": 0.773, "M14-single": 0.688,
                        "M14-flagship-agg": 0.709}),
]
cols = ["metric", "M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11",
        "M12", "M13", "M14", "M15"]
with open(os.path.join(OUT, "MODEL_AUTOPSY_M4_M15_METRICS.csv"), "w",
          newline="") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for name, d in rows:
        w.writerow([name] + [d.get(c, "N/A") for c in cols[1:]])

# ---- charts ----
CH = os.path.join(OUT, "charts")
os.makedirs(CH, exist_ok=True)


def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(CH, name), dpi=120)
    plt.close()


xs = ["M5", "M6", "M7", "M8", "M9int", "M13", "M14"]
plt.figure()
plt.plot(xs, [live_overall[k] for k in xs], marker="o")
plt.title("Live overall score (different project each point — do not trend-read)")
plt.ylabel("overall (M4-family scorer)")
plt.savefig(os.path.join(CH, "01_live_overall.png"), dpi=120)
plt.close()

plt.figure()
plt.plot(xs, [live_discovery[k] for k in xs], marker="o")
plt.title("Live discovery dimension (M5 partial-credit vs M6+ strict)")
plt.ylabel("discovery")
plt.savefig(os.path.join(CH, "02_live_discovery.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(["M4 pipeline\n(n=8, incompatible)", "M9 offline\nmeans",
         "M10 offline", "M13 flagship\nsingle/team",
         "M14 flagship\nagg/single/team"],
        [0.945, 0.938, 0.906, 0.73, 0.723])
plt.title("Offline discovery-type scores (different systems — no trend line)")
plt.ylabel("score")
plt.savefig(os.path.join(CH, "03_offline_discovery.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(xs, [live_tokens[k] for k in xs])
plt.title("Provider-reported live tokens per investigation")
plt.ylabel("tokens")
plt.savefig(os.path.join(CH, "04_live_tokens.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(xs, [live_cost[k] for k in xs])
plt.title("Provider-reported live cost per investigation (USD)")
plt.ylabel("USD")
plt.savefig(os.path.join(CH, "05_live_cost.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(["single", "team"], [0.688, 0.773])
plt.title("Single vs team, one scenario each (M13 b_unit_shift; M14 c_robustness same values)")
plt.ylabel("eval2 aggregate")
plt.savefig(os.path.join(CH, "06_team_vs_single.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(list(tests.keys()), list(tests.values()))
plt.title("Backend tests passing per milestone")
plt.ylabel("tests")
plt.savefig(os.path.join(CH, "07_test_counts.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(["M4 (8 proj)", "M10 (8 scen)"], [0.945, 0.906],
        yerr=[[0.945 - m4ci[0], 0.906 - m10ci[0]],
              [m4ci[1] - 0.945, m10ci[1] - 0.906]],
        capsize=6)
plt.title("Means with bootstrap 95% CIs (within-system only)")
plt.ylabel("mean score")
plt.savefig(os.path.join(CH, "08_means_with_ci.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(["M10 5/8", "live M6-M14\n0-discoveries 6/6"],
        [0.625, 1.0],
        yerr=[[0.625 - wilson(5 / 8, 8)[0], 1.0 - wilson(0.0, 6)[1]],
              [wilson(5 / 8, 8)[1] - 0.625, 0.0]],
        capsize=6)
plt.title("Rates with Wilson 95% CIs")
plt.ylabel("rate")
plt.savefig(os.path.join(CH, "09_rates_wilson_ci.png"), dpi=120)
plt.close()

plt.figure()
plt.bar(["5/5 ran", "1 failed\n(cleanly)", "8/6 breach\n(M7, fixed)"],
        [5, 1, 8])
plt.title("Experiment execution: M5 runs, M5 failure, M7 cap breach")
plt.ylabel("count")
plt.savefig(os.path.join(CH, "10_experiment_outcomes.png"), dpi=120)
plt.close()

print(json.dumps(stats, indent=2))
print("WROTE csv+json+10 charts")
