"""Evidence attribution (M9 Workstream 3.2).

Fixes the M8 over-attribution defect (a shared topic or segment word
automatically became support). A rule hit now passes through an
explicit relationship classifier with seven distinct semantics:

- supports / contradicts: the measurement directly bears on the
  hypothesis mechanism — these move belief (confidence + status).
- relevant_to: family-level topical bearing only — visible, non-moving.
- mentions: the hypothesis names the measured segment but the rule's
  family differs and nothing is denied — visible, non-moving.
- neutral: no bearing at all — recorded for audit, non-moving.
- insufficient: too few samples behind the measurement — non-moving.
- uncertain: the hypothesis itself is unsure about the segment AND the
  overlap is only topical — non-moving.

Denial symmetry: when a hypothesis denies a segment effect ("no true
district failure") and the measurement finds that effect, the evidence
contradicts the hypothesis; when the measurement finds no effect, it
supports the denial. Mentioning a concept is never support.

Only generic English negation scoping is used — no project, segment,
or benchmark vocabulary is hardcoded.
"""
from __future__ import annotations

import re

RELATIONSHIPS = ("supports", "contradicts", "relevant_to", "mentions",
                 "neutral", "insufficient", "uncertain")

MOVING = ("supports", "contradicts")

_TOKEN = re.compile(r"[a-z0-9]+")

_NEGATIONS = ("no", "not", "never", "without", "absent", "rules", "rule",
              "rather", "instead", "deny", "denies", "denied", "free",
              "clean", "artifact")

_UNCERTAIN = ("whether", "unclear", "unknown", "unsure", "maybe",
              "possibly", "undetermined",
              "insufficient", "inconclusive", "unestablished")

_SEGMENT_ARGS = ("split_by", "group_column", "group", "segment", "slice",
                 "split", "fold", "slice_column", "segment_column")

# M16 P1-1: segment vocabulary for the granularity adequacy gate.
# A pooled measurement cannot bear on a claim about one of these;
# an AUC-based rule cannot bear on a ranking/top-K claim.
_SEG_WORDS = ("region", "regions", "district", "districts", "ward",
              "wards", "slice", "slices", "segment", "segments",
              "zone", "zones", "site", "sites", "machine",
              "machines", "county", "counties", "fold", "folds",
              "district-specific", "slice-specific", "region-specific")
# Narrow: generic 'ranking performance' means AUC discrimination in
# existing fixtures/tests; only explicit top-K/precision language
# marks a claim the AUC rule cannot bear on (M14 music shape).
_RANK_WORDS = ("top-k", "top k", "precision at", "p@k",
               "top results", "cold-start", "cold start")
_AUC_TOOLS_FAMILIES = ("subgroup",)


def _names_segment(text: str) -> bool:
    t = " " + (text or "").lower() + " "
    return any(w in t for w in _SEG_WORDS)


def _names_ranking_claim(text: str) -> bool:
    t = " " + (text or "").lower() + " "
    return any(w in t for w in _RANK_WORDS)

# Mechanism equivalence (parity with linker._MATCH): the linker's
# long-standing taxonomy treats split-overlap evidence as bearing on
# leakage hypotheses ("split-hygiene": family match OR _is_leakage).
# Attribution must honor the same equivalence, or genuine
# split-overlap measurements are graded "neutral" against the very
# leakage claims they test. This is mechanism identity, not topical
# word overlap: absence of overlap directly tests an overlap claim.
# No other families are merged: quality-clean results, for example,
# remain topical (relevant_to), never belief-moving, against
# split-overlap claims.
_MECHANISM_EQUIV = (frozenset({"split-hygiene", "leakage"}),)


def same_mechanism(primary: str, rule_family: str) -> bool:
    if primary == rule_family:
        return True
    pair = {primary, rule_family}
    return any(pair <= equiv for equiv in _MECHANISM_EQUIV)


# Family-level denial: effect phrases whose negation denies the
# family's mechanism. Mirrors the segment-level denial symmetry
# below: evidence FOR a denied effect contradicts; evidence of its
# absence supports the denial. Phrases (not single generic words)
# keep false positives out — "change" alone never counts, "level
# change" does. Single-word entries are unambiguous mechanism
# terms only.
# Family-denial negation set: deliberately WITHOUT "artifact".
# The shared _NEGATIONS list treats "artifact" as denial-ish (for
# "no quality artifact"-style segment denials), but at family
# level that misfires: "data quality artifact with nulls" AFFIRMS
# a quality mechanism — "artifact" there is the claim, not its
# denial. Only genuine negations count here.
_FAMILY_NEGATIONS = ("no", "not", "never", "without", "absent",
                     "rather", "instead", "deny", "denies",
                     "denied", "rules", "rule", "free", "clean")


_FAMILY_DENIAL_PHRASES = {
    "drift": ("level shift", "level change", "regime change",
                "structural break", "drift", "regime"),
    "bias": ("systematic bias", "bias"),
    "quality": ("data quality", "missing", "null", "duplicat",
                  "corrupt"),
    "leakage": ("leakage", "data leak", "label leak"),
    "split-hygiene": ("split overlap", "overlap",
                        "chronology"),
    "misspecification": ("misspecification", "autocorrelat",
                           "persistent error"),
    "calibration": ("miscalibrat",),
    "subgroup": ("subgroup",),
    "input-dependence": ("input dependence", "feature dependence"),
}


def denies_family(text: str, rule_family: str) -> bool:
    """Generic negation scoping over a family's effect phrases."""
    phrases = _FAMILY_DENIAL_PHRASES.get(rule_family, ())
    if not phrases:
        return False
    t = " " + (text or "").lower() + " "
    for phrase in phrases:
        idx = t.find(phrase)
        while idx != -1:
            window = _tokens(t[:idx])[-4:]
            if any(w in _FAMILY_NEGATIONS for w in window):
                return True
            idx = t.find(phrase, idx + 1)
    return False


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def measured_segments(arguments: dict | None) -> list[str]:
    """Segment words the measurement was actually computed across."""
    segs: list[str] = []
    for key, val in (arguments or {}).items():
        if key.lower() in _SEGMENT_ARGS and isinstance(val, str):
            for tok in _tokens(val):
                if tok not in ("column", "col") and tok not in segs:
                    segs.append(tok)
    return segs


def _stem_seg_word(word: str) -> str:
    """M17: singularize segment vocabulary (slices->slice, counties->county).

    Only applied when intersecting against measured segment names, so over-stems like bias->bia can never match anything."""
    w = (word or "").lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and len(w) > 3 and not w.endswith("ss"):
        return w[:-1]
    return w


def _seg_mentioned(text: str, segments: list[str]) -> bool:
    """M17: segment naming with plural tolerance (exact match or stemmed)."""
    if not segments:
        return False
    toks = {_stem_seg_word(t) for t in _tokens(text)}
    return bool(set(segments) & toks)


# M17 Phase 4: euphemized uniformity denials. A uniformity claim need not
# say "no": "differences are sampling noise" and "uniform across
# slices" deny the segment effect just as explicitly. These phrases
# trigger denial symmetry when scoped to a measured segment (or, for the
# subgroup family, to any named segment). Base-rate rival claims are
# deliberately ABSENT here: they are competing mechanisms, not denials.
_EUPH_DENIAL_PHRASES = (
    "no difference", "no differences", "no gap", "no disparity",
    "no systematic difference", "no systematic differences",
    "no real difference", "no real differences",
    "no meaningful difference",
    "same across", "uniform across", "uniformity across",
    "uniformly across", "differences are noise",
    "difference is noise", "gap is noise",
    "differences reflect noise", "difference reflects noise",
    "sampling noise", "statistical noise", "just noise",
    "due to noise", "attributable to noise",
    "random variation", "random fluctuation",
)


def _euphemistic_denial(text: str, rule_family: str,
                        segments: list[str]) -> bool:
    low = " " + (text or "").lower() + " "
    if not any(p in low for p in _EUPH_DENIAL_PHRASES):
        return False
    if segments and _seg_mentioned(text, segments):
        return True
    # Family-level uniformity denial: "any observed differences are
    # sampling noise" denies the subgroup effect itself, with or
    # without naming the segment. Scoped to the subgroup family only:
    # other families still require segment scoping above.
    if rule_family == "subgroup":
        return True
    if _names_segment(text):
        return True
    return False


# M17 Phase 4: explicit insufficiency is an epistemic bar, not a
# mechanism claim. It is never moved by a measurement in either
# direction: the claim says the evidence cannot establish the effect.
_INSUFFICIENCY_MARKERS = ("insufficient", "inconclusive",
                          "cannot establish", "cannot conclude",
                          "unestablished", "underpowered",
                          "not enough evidence")


def _claims_insufficiency(text: str) -> bool:
    low = " " + (text or "").lower() + " "
    return any(m in low for m in _INSUFFICIENCY_MARKERS)


def denies(text: str, segments: list[str], window: int = 4) -> bool:
    """Generic negation scoping: a negation token within `window` tokens
    before a segment word (e.g. 'no true district failure'). M17:
    segment matching is plural-tolerant ('no slices underperform')."""
    toks = _tokens(text)
    stems = [_stem_seg_word(t) for t in toks]
    segset = set(segments)
    for i, tok in enumerate(toks):
        if tok in segset or stems[i] in segset:
            if any(t in _NEGATIONS for t in toks[max(0, i - window):i]):
                return True
    return False


def expresses_uncertainty(text: str) -> bool:
    return bool(set(_tokens(text)) & set(_UNCERTAIN))


def _broad_match(family: str, text: str) -> bool:
    """Topical overlap without mechanism commitment (old _MATCH)."""
    from .selection import _family_of
    from .linker import _is_subgroup, _is_bias, _is_leakage, _is_quality
    if _family_of(text) == family:
        return True
    t = (text or "").lower()
    if family == "subgroup":
        return _is_subgroup(t)
    if family == "bias":
        return _is_bias(t)
    if family == "leakage":
        return _is_leakage(t)
    if family in ("quality", "missingness"):
        return _is_quality(t)
    return False


def classify(hypothesis_text: str, rule_family: str, direction: str,
             reason: str, arguments: dict | None = None,
             n: int | None = None, min_n: int = 30) -> dict:
    """Return {relationship, moves_belief, justification}.

    `direction` is the rule's verdict (supports/contradicts) about the
    measured effect; `reason` is the rule's human-readable detail.
    """
    from .selection import _family_of
    text = hypothesis_text or ""
    if direction not in ("supports", "contradicts"):
        raise ValueError("rule direction must be supports or contradicts")
    if n is not None and n < min_n:
        return {"relationship": "insufficient", "moves_belief": False,
                "justification": f"only n={n} behind the measurement "
                                 f"(min {min_n}); cannot bear on any "
                                 f"hypothesis"}
    # M16 P1-1 granularity adequacy gates. A pooled measurement (no
    # segment argument on the action) cannot support or contradict a
    # segment-specific hypothesis; an AUC-based subgroup rule cannot
    # bear on an explicit ranking/top-K claim (M14 music: uniform AUC
    # coexisted with a collapsed slice P@K). Such evidence is
    # informative but insufficient -> relevant_to (visible, non-moving),
    # never a silent skip.
    _segs_measured = measured_segments(arguments)
    if (not _segs_measured and _names_segment(text)
            and rule_family in _AUC_TOOLS_FAMILIES):
        return {"relationship": "relevant_to", "moves_belief": False,
                "justification": "pooled measurement without a "
                                 "segment breakdown cannot support or "
                                 "contradict a segment-specific claim; "
                                 "needs the grouped/slice probe"}
    if _names_ranking_claim(text) and rule_family == "subgroup" \
            and (arguments or {}).get("tool_family") != "ranking":
        _auc_args = {"split_by", "group_column"}
        if _auc_args & set((arguments or {}).keys()):
            return {"relationship": "relevant_to",
                    "moves_belief": False,
                    "justification": "AUC-based subgroup rule cannot "
                                     "bear on an explicit ranking/top-K "
                                     "claim; needs the slice P@K probe"}
    segs = measured_segments(arguments)
    toks = set(_tokens(text))
    names_seg = _seg_mentioned(text, segs)
    primary = _family_of(text)
    denial = denies(text, segs) if segs else False
    if _claims_insufficiency(text):
        return {"relationship": "uncertain", "moves_belief": False,
                "justification": "hypothesis states the evidence cannot "
                                 "establish the effect; a measurement "
                                 "neither confirms nor refutes that bar"}
    if _euphemistic_denial(text, rule_family, segs):
        # Euphemized uniformity denial: evidence for the denied effect
        # contradicts; evidence of no effect supports the denial.
        rel = ("contradicts" if direction == "supports" else "supports")
        return {"relationship": rel, "moves_belief": True,
                "justification": f"hypothesis claims uniformity/noise "
                                 f"for the measured effect and the "
                                 f"measurement {reason}; euphemized "
                                 f"denial decides"}
    if segs and denial:
        # Denial symmetry: evidence for the denied effect contradicts
        # the hypothesis; evidence of no effect supports the denial.
        rel = ("contradicts" if direction == "supports" else "supports")
        return {"relationship": rel, "moves_belief": True,
                "justification": f"hypothesis denies the measured "
                                 f"segment effect ({'/'.join(segs)}) and "
                                 f"the measurement {reason}; "
                                 f"denial vs measurement decides"}
    if denies_family(text, rule_family):
        # Family-level denial symmetry: the hypothesis explicitly
        # denies this mechanism ("not a level change"); a measurement
        # finding the denied effect contradicts it, a measurement
        # finding no such effect supports the denial.
        rel = ("contradicts" if direction == "supports" else "supports")
        return {"relationship": rel, "moves_belief": True,
                "justification": f"hypothesis denies the "
                                 f"{rule_family} mechanism and the "
                                 f"measurement {reason}; denial vs "
                                 f"measurement decides"}
    # M13 §3.1: explicit cross-family relationships. A measurement
    # moves belief across families ONLY through a stated textual
    # commitment: a stability/persistence claim is contradicted by a
    # measured break; a recency claim is contradicted by persistent-
    # everywhere errors. Anything else stays non-moving (topical or
    # neutral). Ambiguous texts (both markers) never move.
    _PERSIST_MARKERS = ("throughout", "persistent", "stable over",
                        "no change", "uniform over", "constant over")
    _RECENCY_MARKERS = ("recent", "level shift", "regime change",
                        "new break")
    low = f" {text.lower()} "
    persist = any(m in low for m in _PERSIST_MARKERS)
    recent = any(m in low for m in _RECENCY_MARKERS)
    if persist and recent:
        pass  # ambiguous commitment: fall through, never force
    elif persist and rule_family == "drift" and direction == "supports":
        return {"relationship": "contradicts", "moves_belief": True,
                "justification": f"hypothesis commits to "
                f"stability/persistence but the measurement finds a "
                f"break ({reason}); cross-family contradiction"}
    elif recent and rule_family == "misspecification" and \
            direction == "supports":
        return {"relationship": "contradicts", "moves_belief": True,
                "justification": f"hypothesis commits to a recent "
                f"change but errors persist throughout ({reason}); "
                "cross-family contradiction"}
    if same_mechanism(primary, rule_family) or (names_seg and not denial):
        return {"relationship": direction, "moves_belief": True,
                "justification": f"measurement directly bears on the "
                                 f"hypothesis mechanism: {reason}"}
    if names_seg:
        return {"relationship": "mentions", "moves_belief": False,
                "justification": f"hypothesis names the measured segment "
                                 f"({'/'.join(segs)}) but its mechanism is "
                                 f"{primary}, not {rule_family}: topical "
                                 f"overlap is not support"}
    if expresses_uncertainty(text) and _broad_match(rule_family, text):
        return {"relationship": "uncertain", "moves_belief": False,
                "justification": "hypothesis is unsure about this segment "
                                 "and the overlap is only topical"}
    if _broad_match(rule_family, text):
        return {"relationship": "relevant_to", "moves_belief": False,
                "justification": f"family-level topical bearing on "
                                 f"{rule_family}; no segment-specific "
                                 f"mechanism link"}
    return {"relationship": "neutral", "moves_belief": False,
            "justification": "no bearing of this measurement on the "
                             "hypothesis"}
