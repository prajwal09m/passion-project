"""Research orchestration driver (Parts 1, 3-7 glue).

run_autonomous_investigation() executes the 11-stage pipeline with
explicit per-stage state, inputs, outputs and provenance events. The
default reasoner is None -> deterministic offline triage (used by tests,
challenge suite, flagship demo). A provider-backed reasoner can be
injected later with the same interface; the driver never imports
providers itself.
"""
from __future__ import annotations

from . import recon as _recon
from . import hypotheses as _hyp
from . import experiments as _exp
from . import verification as _ver

STAGES = ["project_understanding", "reconnaissance", "planning",
          "hypothesis_generation", "diagnostic_selection",
          "experiment_design", "experiment_execution",
          "result_interpretation", "hypothesis_revision",
          "independent_verification", "final_reporting"]


def _stage(session, inv, name: str, output: dict) -> None:
    import copy as _copy
    from ..db import record_event
    rs = _copy.deepcopy(dict((inv.config or {}).get("research") or {}))
    stages = dict(rs.get("stages") or {})
    stages[name] = output
    rs["stages"] = stages
    inv.config = {**(inv.config or {}), "research": rs}
    session.commit()
    record_event(session, inv.id, "tool_result",
                 f"Research stage: {name}",
                 payload={"stage": name,
                          "keys": sorted(output.keys())[:10]})
    session.commit()


def _triage_hypotheses(understanding: dict, spec) -> list[dict]:
    """Offline deterministic hypothesis generator (evidence-motivated).

    Rules inspect the real understanding doc (columns, temporal hints,
    availability) plus light artifact statistics supplied by the caller.
    No hardcoded failure answers: each card states observables + refute
    criteria so wrong guesses get rejected by experiments.
    """
    cols = ((understanding.get("receives") or {}).get("columns")) or []
    has = lambda *names: any(c in cols for c in names)
    task = getattr(spec, "task_type", "other")
    cards: list[dict] = []
    if task == "classification" and has("label", "score"):
        cards.append({
            "title": "Proxy feature leaks the label",
            "mechanism": "A feature mirrors the target (possible "
                         "post-outcome or join-key leak); the model may "
                         "exploit it instead of generalizing.",
            "evidence_motivating": ["classification task with label+score "
                                    "present; leakage screen applicable"],
            "expected_observables": ["one feature correlates with label "
                                     "far above the rest (>0.5 gap)"],
            "diagnostics": ["feature_target_suspiciousness"],
            "support_criteria": "top |correlation| >= 0.7 and a clear gap "
                                "to the next feature",
            "refute_criteria": "all |correlations| modest (<0.4) or top "
                               "feature is a legitimate driver",
            "priority": "high"})
        cards.append({
            "title": "Subgroup underperformance hidden by pooled metric",
            "mechanism": "Strong overall AUC can conceal a failing slice "
                         "(ward/segment); pooled metric conceals the mode.",
            "evidence_motivating": ["segment-like columns present"],
            "expected_observables": ["per-segment metric spread is large"],
            "diagnostics": ["classification_metrics"],
            "support_criteria": "a segment AUC >= 0.1 below the best",
            "refute_criteria": "segment AUCs within 0.03 of each other",
            "priority": "medium"})
    if task == "regression" and has("target", "prediction"):
        cards.append({
            "title": "Systematic bias in one segment",
            "mechanism": "Additive offset for a subgroup (e.g. pricing "
                         "rule) shifts predictions one way.",
            "evidence_motivating": ["segment column present alongside "
                                    "target/prediction"],
            "expected_observables": ["mean residual differs by segment "
                                     "by a material amount"],
            "diagnostics": ["regression_metrics"],
            "support_criteria": "|segment bias gap| large vs residual std",
            "refute_criteria": "segment biases within noise of each other",
            "priority": "high"})
    if task == "forecasting" and has("target", "prediction"):
        cards.append({
            "title": "Stale validation split hides drift",
            "mechanism": "Overlapping or shuffled train/test windows leak "
                         "recent history; the model misses drift that a "
                         "chronological split would expose.",
            "evidence_motivating": ["date + split columns present"],
            "expected_observables": ["split date spans overlap; late "
                                     "error >> early error"],
            "diagnostics": ["forecast_diagnostics"],
            "support_criteria": "overlap present AND late MAE >= 1.5x "
                                "early MAE",
            "refute_criteria": "spans disjoint and error flat over time",
            "priority": "high"})
    if task == "clustering":
        cards.append({
            "title": "Segments unstable or imbalanced",
            "mechanism": "Weak separation yields low silhouette or a "
                         "degenerate giant cluster.",
            "evidence_motivating": ["numeric feature columns present"],
            "expected_observables": ["silhouette < 0.4 or imbalance "
                                     "ratio > 5"],
            "diagnostics": ["clustering_stability"],
            "support_criteria": "silhouette < 0.4 or imbalance > 5",
            # Calibrated 2026-11-01 (M4): k-means k=3 on unstructured
            # Gaussian data yields silhouette ~=0.34 (sigma sweep
            # 1.5-3.0), so <0.3 is nearly unreachable and weak
            # structure goes undetected. <0.4 = weak/unstable.
            "refute_criteria": "silhouette >= 0.5 with balance < 2",
            "priority": "medium"})
    if task == "ranking":
        cards.append({
            "title": "Ranking metric conceals position failure",
            "mechanism": "Pooled NDCG looks fine while top-K precision "
                         "collapses for a query slice.",
            "evidence_motivating": ["rank/score columns present"],
            "expected_observables": ["per-slice P@K spread large"],
            "diagnostics": ["ranking_diagnostics"],
            "support_criteria": "slice P@K gap >= 0.2",
            "refute_criteria": "slices agree within 0.05",
            "priority": "medium"})
    cards.append({
        "title": "No material issue (null hypothesis)",
        "mechanism": "The system may be healthy; apparent anomalies are "
                     "noise. Correct conclusion when nothing replicates.",
        "evidence_motivating": ["base-rate guard against false alarms"],
        "expected_observables": ["all diagnostics within normal bands"],
        "diagnostics": ["dataset_validation"],
        "support_criteria": "no diagnostic breaches its threshold",
        "refute_criteria": "any diagnostic breaches with review upheld",
        "priority": "low"})
    return cards


def run_autonomous_investigation(session, inv, spec,
                                 artifact_path: str | None = None,
                                 max_experiments: int = 4) -> dict:
    """Full offline autonomous cycle; returns the final forensic report."""
    from .. import task_diagnostics as _td
    from ..db import record_event
    understanding = _recon.build_understanding(spec)
    _stage(session, inv, "project_understanding",
           {"predicting": understanding["predicting"],
            "possible": understanding["possible"],
            "impossible": understanding["impossible"],
            "missing": understanding["missing"]})
    _stage(session, inv, "reconnaissance",
           {"columns": (understanding.get("receives") or {}).get(
               "columns", []),
            "inconsistencies": understanding.get("inconsistencies", [])})
    _stage(session, inv, "planning",
           {"strategy": "hypothesis-led; smallest useful experiment "
                        "first; null hypothesis always present"})
    proposed = []
    for card in _triage_hypotheses(understanding, spec):
        try:
            proposed.append(_hyp.propose(session, inv, card))
        except ValueError:
            pass
    _stage(session, inv, "hypothesis_generation",
           {"n": len(proposed),
            "ids": [c["id"] for c in proposed]})
    try:
        from ..projects import get_project as _gp
        caps = _gp(spec.project_id).available_capabilities()
    except Exception:
        # Unregistered ad-hoc spec: honest read-only defaults matching the
        # black-box adapter (inputs/outputs observable, no white-box). This
        # keeps leakage screens available instead of silently blocking them.
        caps = ["prediction_inspection", "error_analysis", "calibration",
                "data_leakage_checks", "reproducibility"]
    avail = {c: True for c in (
        (understanding.get("receives") or {}).get("columns", []))}
    avail.update({"label": "label" in avail, "score": "score" in avail,
                  "target": "target" in avail,
                  "prediction": "prediction" in avail,
                  "features": True, "date": "date" in avail})
    sel = _td.select_tools(spec.task_type, caps, avail)
    _stage(session, inv, "diagnostic_selection", sel)
    selected = sel.get("selected", [])
    _stage(session, inv, "experiment_design",
           {"budgets": {"max_experiments": max_experiments},
            "heuristic_note": _exp.HEURISTIC_NOTE})
    results, veredicts = [], []
    for card in _hyp.list_cards(inv)[:max_experiments + 1]:
        if card["title"].startswith("No material issue"):
            continue
        if len(results) >= max_experiments:
            break
        diag = [d for d in (card.get("diagnostics") or [])
                if d in selected] or (selected[:1] if selected else [])
        if not diag:
            _hyp.transition(session, inv, card["id"], "blocked",
                            "no selected diagnostic covers this hypothesis")
            continue
        _hyp.transition(session, inv, card["id"], "investigating",
                        "experiment dispatched")
        plan = _exp.design({**card, "diagnostics": diag}, selected)
        plan["artifact"] = artifact_path or spec.dataset.location
        res = _run_plan(plan, spec)
        results.append(res)
        _hyp.transition(
            session, inv, card["id"],
            "supported" if res.get("breach") else "rejected",
            res.get("summary", ""),
            evidence=[{"experiment_id": res["experiment_id"],
                       "tool": res["tool"],
                       "numbers": res.get("numbers", {})}])
        claim = {"summary": card["title"],
                 "n": res.get("numbers", {}).get("n", 0),
                 "method": res.get("tool", ""),
                 "numbers": res.get("numbers", {}),
                 "refute_criteria": card.get("refute_criteria")}
        review = _ver.review_claim(claim, [res.get("numbers", {})])
        _ver.record_review(session, inv, card["id"], review)
        veredicts.append({"hypothesis_id": card["id"], **review})
    _stage(session, inv, "experiment_execution",
           {"n": len(results),
            "ids": [r["experiment_id"] for r in results]})
    _stage(session, inv, "result_interpretation",
           {"summaries": [r.get("summary", "")[:160] for r in results]})
    _stage(session, inv, "hypothesis_revision",
           {"cards": [(c["id"][:8], c["status"])
                      for c in _hyp.list_cards(inv)]})
    _stage(session, inv, "independent_verification",
           {"verdicts": [(v["hypothesis_id"][:8], v["verdict"])
                         for v in veredicts]})
    report = build_forensic_report(inv, understanding, results,
                                   veredicts)
    _stage(session, inv, "final_reporting",
           {"confirmed": len(report["confirmed_findings"]),
            "rejected": len(report["rejected_hypotheses"])})
    record_event(session, inv.id, "report",
                 "Autonomous forensic report assembled",
                 payload={"confirmed": len(report["confirmed_findings"])})
    session.commit()
    import copy as _copy2
    rs = _copy2.deepcopy(dict((inv.config or {}).get("research") or {}))
    rs["report"] = report
    inv.config = {**(inv.config or {}), "research": rs}
    session.commit()
    return report


def _run_plan(plan: dict, spec) -> dict:
    """Dispatch one plan to the real deterministic diagnostic."""
    from .. import task_diagnostics as _td
    tool, art = plan["tool"], plan.get("artifact")
    numbers: dict = {}
    breach, summary = False, ""
    try:
        if tool == "feature_target_suspiciousness":
            from .. import ml_tools as _ml
            import pandas as pd
            df = pd.read_csv(art)
            label = "label" if "label" in df.columns else None
            feats = [c for c in df.columns
                     if c not in ("label", "score", "fold")]
            best, gap = None, 0.0
            corrs = {}
            for c in feats:
                try:
                    v = pd.to_numeric(df[c], errors="coerce")
                    if v.notna().sum() < 10 or v.nunique() < 2:
                        continue
                    r = float(v.corr(df[label])) if label else 0.0
                    corrs[c] = round(r, 4)
                except Exception:
                    continue
            if not corrs:
                numbers = {"n": len(df)}
                breach = False
                summary = ("no feature columns present; leakage screen "
                           "inapplicable with predictions-only input")
            else:
                ranked = sorted(corrs.items(),
                                key=lambda kv: -abs(kv[1]))
                best = ranked[0]
                gap = abs(ranked[0][1]) - (abs(ranked[1][1])
                                           if len(ranked) > 1 else 0.0)
                numbers = {"n": len(df), "top_feature": best[0],
                           "top_corr": best[1], "gap": round(gap, 4)}
                breach = abs(best[1]) >= 0.7 and gap >= 0.2
                summary = (f"top feature {best[0]} |r|={abs(best[1]):.3f} "
                           f"(gap {gap:.3f})")
        elif tool == "classification_metrics":
            import pandas as pd
            from sklearn.metrics import roc_auc_score
            df = pd.read_csv(art)
            cols = [c for c in df.columns if c not in ("label",)]
            score = "score" if "score" in df.columns else (
                cols[0] if cols else None)
            if score and "label" in df.columns:
                auc = float(roc_auc_score(df["label"], df[score]))
                numbers = {"n": len(df), "auc": round(auc, 4)}
                # Pooled AUC can conceal a failing slice: check any
                # categorical column for per-group spread.
                gcol = next((c for c in df.columns
                             if c not in ("label", score, "fold")
                             and df[c].dtype == object), None)
                gap = 0.0
                if gcol:
                    per = {}
                    for g, ch in df.groupby(gcol):
                        if ch["label"].nunique() > 1:
                            per[str(g)] = round(float(roc_auc_score(
                                ch["label"], ch[score])), 4)
                    numbers["auc_by_group"] = per
                    numbers["group_column"] = gcol
                    if len(per) >= 2:
                        gap = max(per.values()) - min(per.values())
                numbers["group_gap"] = round(gap, 4)
                breach = auc < 0.6 or gap >= 0.1
                summary = f"AUC={auc:.3f} via {score}" + \
                    (f" group_gap={gap:.3f}({gcol})" if gcol else "")
        elif tool == "regression_metrics":
            import pandas as _pd
            _frame = _pd.read_csv(art, nrows=2000)
            _gcol = next((c for c in _frame.columns
                          if c not in ("target", "prediction", "date")
                          and _frame[c].dtype == object), None)
            out = _td.regression_metrics(
                art, group_column=_gcol) if _gcol else _td.regression_metrics(art)
            numbers = {"n": out["n"], "mae": round(out["mae"], 2),
                       "bias": round(out["bias_mean_residual"], 2),
                       "groups": out.get("mae_by_group", {})}
            g = numbers["groups"]
            # Residual-vs-feature correlation catches preprocessing-scale
            # mismatches that hit every segment equally (no group spread).
            _maxfcorr, _feat = 0.0, None
            try:
                _y = _pd.to_numeric(_frame["target"],
                                    errors="coerce")
                _p = _pd.to_numeric(_frame["prediction"],
                                    errors="coerce")
                _r = (_y - _p)
                for c in _frame.columns:
                    if c in ("target", "prediction", "date"):
                        continue
                    v = _pd.to_numeric(_frame[c], errors="coerce")
                    if v.notna().sum() > 10 and v.nunique() > 2:
                        _cc = float(_r.corr(v))
                        if abs(_cc) > abs(_maxfcorr):
                            _maxfcorr, _feat = _cc, c
            except Exception:
                pass
            numbers["residual_feature_corr"] = round(_maxfcorr, 3)
            numbers["residual_feature"] = _feat
            breach = (len(g) >= 2 and (
                max(g.values()) >= 2 * min(g.values())
                or abs(out["bias_mean_residual"]) > 5000)) \
                or abs(out["bias_mean_residual"]) > 5000 \
                or abs(_maxfcorr) > 0.5
            summary = (f"MAE={out['mae']:.0f} bias={numbers['bias']} "
                       f"featcorr={_feat}:{_maxfcorr:.2f}")
        elif tool == "forecast_diagnostics":
            out = _td.forecast_diagnostics(art,
                                           split_column="split"
                                           if "split" in str(
                                               open(art).read(2000))
                                           else None)
            d = out.get("drift_early_vs_late_mae", [])
            numbers = {"n": out["n"], "drift": d,
                       "overlap": out.get("split_overlap_hint")}
            breach = bool(out.get("split_overlap_hint")) or (
                len(d) == 2 and d[0] and d[1] / max(d[0], 1e-9) >= 1.5)
            summary = f"drift={d} overlap={numbers['overlap']}"
        elif tool == "clustering_stability":
            out = _td.clustering_stability(art)
            numbers = {"n": out["n"],
                       "silhouette": round(out["silhouette"], 3),
                       "imbalance": round(out["imbalance_ratio"], 3)}
            breach = out["silhouette"] < 0.4 or out[
                "imbalance_ratio"] > 5
            summary = (f"silhouette={numbers['silhouette']} "
                       f"imbalance={numbers['imbalance']}")
        elif tool in ("ranking_diagnostics", "dataset_validation"):
            numbers, summary = _run_generic(art, tool)
            breach = bool(numbers.get("breach"))
        else:
            numbers, summary = _run_generic(art, tool)
            breach = False
    except Exception as exc:
        summary = f"{tool} failed: {type(exc).__name__}"
    return {"experiment_id": plan["experiment_id"],
            "hypothesis_id": plan.get("hypothesis_id"),
            "tool": tool, "status": "ran", "breach": breach,
            "summary": summary, "numbers": numbers}


def _run_generic(art: str, tool: str) -> tuple[dict, str]:
    import pandas as pd
    try:
        df = pd.read_csv(art, nrows=2000)
    except Exception:
        return {"n": 0}, "artifact unreadable"
    if tool == "ranking_diagnostics":
        # Per-query top-K precision averaged by slice: pooled means can
        # conceal a collapsing slice, so the slice gap is the signal.
        rel = next((c for c in ("relevance", "label", "target")
                    if c in df.columns), None)
        grp = next((c for c in df.columns
                    if c.lower() in ("slice", "group", "segment",
                                     "query_slice")), None)
        score = next((c for c in ("score", "prediction", "rank_score")
                      if c in df.columns), None)
        qid = next((c for c in ("query", "query_id", "qid")
                    if c in df.columns), None)
        if rel and grp and score:
            if qid:
                per_q = []
                for (q, g), ch in df.groupby([qid, grp]):
                    k = min(5, len(ch))
                    top = ch.nlargest(k, score)
                    per_q.append(
                        (str(g), float(top[rel].mean())))
                import collections as _co
                acc: dict = _co.defaultdict(list)
                for g, v in per_q:
                    acc[g].append(v)
                slices = {g: float(sum(v) / len(v))
                          for g, v in acc.items()}
            else:
                slices = {}
                for g, ch in df.groupby(grp):
                    top = ch.nlargest(min(10, len(ch)), score)
                    slices[str(g)] = float(top[rel].mean())
            vals = list(slices.values())
            gap = max(vals) - min(vals) if vals else 0.0
            return {"n": len(df), "p_at_k_by_slice": slices,
                    "gap": round(gap, 4), "breach": gap >= 0.2}, \
                f"slice P@K gap={gap:.3f}"
        return {"n": len(df)}, "ranking columns incomplete"
    n, cols = len(df), list(df.columns)
    return {"n": n, "columns": cols}, f"schema: {n} rows x {len(cols)} cols"


def build_forensic_report(inv, understanding: dict, results: list,
                          veredicts: list) -> dict:
    cards = _hyp.list_cards(inv)
    confirmed = [{"hypothesis_id": c["id"], "title": c["title"],
                  "mechanism": c["mechanism"],
                  "evidence": c.get("evidence_motivating", [])}
                 for c in cards if c["status"] == "supported"]
    rejected = [{"hypothesis_id": c["id"], "title": c["title"]}
                for c in cards if c["status"] == "rejected"]
    inconc = [{"hypothesis_id": c["id"], "title": c["title"]}
              for c in cards if c["status"] in ("inconclusive",
                                                "blocked")]
    open_h = [{"hypothesis_id": c["id"], "title": c["title"],
               "status": c["status"]} for c in cards
              if c["status"] in ("proposed", "investigating")]
    return {
        "executive_summary":
            f"{len(confirmed)} supported / {len(rejected)} rejected / "
            f"{len(inconc)} inconclusive-or-blocked from "
            f"{len(results)} experiment(s).",
        "project_understanding": understanding,
        "confirmed_findings": confirmed,
        "rejected_hypotheses": rejected,
        "inconclusive": inconc,
        "open_hypotheses": open_h,
        "experiments": results,
        "verification": veredicts,
        "limitations": [
            "offline deterministic triage; LLM reasoning quality "
            "covered by prior frozen live campaigns, not here",
            "single scenario per task family in this suite slice",
            "heuristic prioritization is not Bayesian information gain",
        ],
        "reproducibility": {"seeds": "fixed per diagnostic",
                            "artifacts": "committed CSV fixtures",
                            "runner": "lab.run_autonomous_investigation"},
        "recommendations": [
            "re-run breached diagnostics on fresh splits before acting",
            "add a reusable diagnostic module for any candidate novel "
            "mechanism before treating it as a finding type"],
    }
