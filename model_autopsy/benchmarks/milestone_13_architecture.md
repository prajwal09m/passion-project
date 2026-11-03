# M13 Architecture

M13 builds on M9-M12: ontology (research/ontology.py, 19 dimensions), invention with info_value (research/invention.py), adaptive agenda (research/agenda.py detect_pivot/revise_on_evidence), autonomous loop (research/autonomous.py + segment-grounded seed), attribution with cross-family rules (causal/attribution.py), team (m11/team.py mandatory skeptic + investigator response + judge), knowledge (m12/knowledge.py) + verify (m12/verify.py manifests), eval2 (m10/eval2.py) + corpus B (m10/scenarios_b.py + fixture_m10b), portfolio (m12/portfolio.py) + scheduler/authorization, adapters (model_adapters honest guarded TF/HF), dashboard (Lab.tsx workspace + /api/lab/portfolio|knowledge|corpus-b).

Baseline M9-M12 preserved. Backend suites green. Frontend tsc + vite pass.
