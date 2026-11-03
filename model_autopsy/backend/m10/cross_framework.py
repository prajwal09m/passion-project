"""M10 cross-framework validation (offline, honest coverage).

Exercises real framework models (fit + predict) and routes their
predictions through the REAL diagnostic tools. Frameworks that are
not installed are REPORTED as unvalidated — never claimed.
"""
from __future__ import annotations


def check_sklearn() -> dict:
    """LogisticRegression + RandomForest on a synthetic tabular task."""
    try:
        from sklearn.datasets import make_classification
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        return {"framework": "scikit-learn", "available": False,
                "reason": str(exc)}
    import csv
    from ..config import PROJECT_ROOT as _PR
    _tmp = _PR / "model_autopsy" / ".m10_work"
    _tmp.mkdir(exist_ok=True)
    X, y = make_classification(n_samples=600, n_features=8,
                               n_informative=5, random_state=7)
    Xa, Xe, ya, ye = train_test_split(X, y, test_size=0.3,
                                      random_state=7)
    ops = {}
    for name, clf in (("logreg", LogisticRegression(max_iter=500)),
                      ("rf", RandomForestClassifier(n_estimators=20,
                                                    random_state=7))):
        clf.fit(Xa, ya)
        proba = clf.predict_proba(Xe)[:, 1]
        path = f"model_autopsy/.m10_work/sk_{name}.csv"
        _abs = str(_tmp / f"sk_{name}.csv")
        with open(_abs, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["label", "score"])
            w.writerows(([int(t), round(float(p), 4)]
                         for t, p in zip(ye, proba)))
        ops[name] = {"fitted": True, "n_test": len(ye),
                     "predictions": path}
    from ..ml_tools import classification_metrics as CM
    diag = {}
    for name, op in ops.items():
        try:
            r = CM(predictions_path=op["predictions"],
                   score_column="score")
            diag[name] = {"ok": True, "auc": r.get("auc")}
        except Exception as exc:
            diag[name] = {"ok": False, "reason": str(exc)[:150]}
    return {"framework": "scikit-learn", "available": True,
            "supported_ops": ["fit", "predict_proba",
                              "classification_metrics"],
            "unsupported_ops": [],
            "diagnostics": diag}


def check_torch() -> dict:
    """Tiny MLP regressor -> predictions CSV -> regression_metrics."""
    try:
        import torch
        import torch.nn as nn
    except ImportError as exc:
        return {"framework": "pytorch", "available": False,
                "reason": str(exc)}
    import csv
    from ..config import PROJECT_ROOT as _PR2
    _tmp2 = _PR2 / "model_autopsy" / ".m10_work"
    _tmp2.mkdir(exist_ok=True)
    torch.manual_seed(11)
    n = 400
    X = torch.randn(n, 4)
    y = 2 * X[:, 0] - X[:, 1] + 0.3 * torch.randn(n)
    net = nn.Sequential(nn.Linear(4, 16), nn.ReLU(), nn.Linear(16, 1))
    opt = torch.optim.Adam(net.parameters(), lr=0.05)
    for _ in range(60):
        opt.zero_grad()
        loss = ((net(X).squeeze() - y) ** 2).mean()
        loss.backward()
        opt.step()
    with torch.no_grad():
        pred = net(X).squeeze().tolist()
    _torch_rel = "model_autopsy/.m10_work/torch_reg.csv"
    import os as _os
    with open(_os.path.join(str(_tmp2), "torch_reg.csv"), "w",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["target", "prediction"])
        w.writerows(([round(float(t), 4), round(float(p), 4)]
                     for t, p in zip(y.tolist(), pred)))
    from ..task_diagnostics import regression_metrics as RM
    try:
        r = RM(predictions_path=_torch_rel)
        diag = {"ok": True, "r2": r.get("r2")}
    except Exception as exc:
        diag = {"ok": False, "reason": str(exc)[:150]}
    return {"framework": "pytorch", "available": True,
            "supported_ops": ["fit-mlp", "predict",
                              "regression_metrics"],
            "unsupported_ops": ["sequence models (not exercised)"],
            "diagnostics": diag}


def check_unavailable() -> list[dict]:
    out = []
    try:
        import tensorflow  # noqa
        out.append({"framework": "tensorflow", "available": True,
                    "note": "installed but NOT exercised: no validated "
                            "claims"})
    except ImportError:
        out.append({"framework": "tensorflow", "available": False,
                    "reason": "not installed: no validation claimed"})
    try:
        import transformers  # noqa
        out.append({"framework": "huggingface", "available": True,
                    "note": "installed but NOT exercised: no validated "
                            "claims"})
    except ImportError:
        out.append({"framework": "huggingface", "available": False,
                    "reason": "not installed: no validation claimed"})
    return out


def validate_all() -> dict:
    return {"sklearn": check_sklearn(), "torch": check_torch(),
            "other": check_unavailable()}
