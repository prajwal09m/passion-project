"""Safe static Python inspection (no execution, no imports).

Parses source with `ast` only. Reports pipeline structure (imports,
preprocessing, split, fit, eval order) and heuristic warnings that are
explicitly *suspicions*, never proof of leakage. Malformed files fail
safely with a recorded error.
"""
from __future__ import annotations

import ast
from pathlib import Path

from . import config

SUSPICIOUS_PATTERNS = (
    ("fit_transform", "global fit_transform before split — may fit preprocessing on the full data"),
    ("fillna", "target-aware imputation pattern — verify fill values do not use the label"),
    ("target", "references to target/label columns in feature construction — verify timing"),
    ("leak", "identifier literally mentions leakage — inspect manually"),
)


def inspect_script(script_path: str, max_chars: int = 200_000) -> dict:
    """Parse a project-relative .py file without executing it."""
    rel = _resolve(script_path)
    text = rel.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        text = text[:max_chars]
    try:
        tree = ast.parse(text, filename=rel.name)
    except SyntaxError as exc:
        return {"ok": False, "source": str(rel), "error": f"syntax error line {exc.lineno}: {exc.msg}",
                "executed": False}
    imports: list[str] = []
    calls: list[dict] = []  # {line, func}
    assigns_target: list[dict] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                imports.extend(a.name.split(".")[0] for a in node.names)
            else:
                imports.append((node.module or "").split(".")[0])
        if isinstance(node, ast.Call):
            f = node.func
            name = ""
            if isinstance(f, ast.Attribute):
                name = f.attr
            elif isinstance(f, ast.Name):
                name = f.id
            if name:
                calls.append({"line": getattr(node, "lineno", 0), "func": name})
        if isinstance(node, ast.Assign):
            for t in node.targets:
                names = _target_names(t)
                if any("target" in n.lower() or n.lower() in ("y", "label") for n in names):
                    assigns_target.append({"line": getattr(node, "lineno", 0), "targets": names})
    # order analysis: first split-like call vs first fit-like call
    def first(pred) -> int | None:
        ls = [c["line"] for c in calls if pred(c["func"])]
        return min(ls) if ls else None
    split_kw = ("train_test_split", "TimeSeriesSplit", "KFold", "StratifiedKFold", "split")
    fit_kw = ("fit", "fit_transform", "fit_predict")
    first_split = first(lambda f: any(k.lower() in f.lower() for k in split_kw))
    first_fit = first(lambda f: any(k.lower() in f.lower() for k in fit_kw))
    order_note = None
    if first_fit is not None and first_split is not None and first_fit < first_split:
        order_note = f"fit-like call at line {first_fit} precedes first split-like call at line {first_split}: preprocessing may be fitted before splitting (suspicion only — verify data flow)."

    warnings: list[dict] = []
    lowered = text.lower()
    for key, msg in SUSPICIOUS_PATTERNS:
        if key in lowered:
            lines = [i + 1 for i, l in enumerate(text.splitlines()) if key in l.lower()][:5]
            warnings.append({"pattern": key, "message": msg, "lines": lines})
    if order_note:
        warnings.insert(0, {"pattern": "fit_before_split", "message": order_note,
                            "lines": [first_fit, first_split]})

    return {
        "ok": True,
        "source": str(rel),
        "executed": False,
        "note": "Static inspection only: code was parsed, never executed or imported. Patterns are suspicions, not proof of leakage.",
        "imports": sorted(set(imports))[:30],
        "n_calls": len(calls),
        "first_split_line": first_split,
        "first_fit_line": first_fit,
        "target_assignments": assigns_target[:10],
        "warnings": warnings,
    }


def _target_names(t) -> list[str]:
    if isinstance(t, ast.Name):
        return [t.id]
    if isinstance(t, (ast.Tuple, ast.List)):
        out = []
        for e in t.elts:
            out.extend(_target_names(e))
        return out
    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
        return [t.value.id]
    return []


def _resolve(p: str) -> Path:
    from . import config as _cfg
    path = _cfg.resolve_restricted(p)
    if not path.exists():
        raise FileNotFoundError(f"artifact not found: {path}")
    if path.suffix.lower() != ".py":
        raise ValueError("script_static_inspection requires a .py file")
    return path
