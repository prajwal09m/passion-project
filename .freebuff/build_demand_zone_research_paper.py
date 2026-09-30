from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile
import hashlib
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Demand_Zone_AI_Autonomy_Study.docx"

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
DC = "http://purl.org/dc/elements/1.1/"
DCT = "http://purl.org/dc/terms/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
VT = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("w", W)
ET.register_namespace("r", R)
ET.register_namespace("", REL)


def q(ns, tag):
    return "{%s}%s" % (ns, tag)


def add(parent, ns, tag, attrs=None, text=None):
    node = ET.SubElement(parent, q(ns, tag), attrs or {})
    if text is not None:
        node.text = str(text)
    return node


def set_text_run(parent, text, bold=False, italic=False, code=False, color=None, size=None):
    r = add(parent, W, "r")
    props = add(r, W, "rPr")
    if bold:
        add(props, W, "b")
    if italic:
        add(props, W, "i")
    if code:
        add(props, W, "rFonts", {q(W, "ascii"): "Consolas", q(W, "hAnsi"): "Consolas"})
        add(props, W, "sz", {q(W, "val"): "17"})
        add(props, W, "color", {q(W, "val"): "365F91"})
    if color:
        add(props, W, "color", {q(W, "val"): color})
    if size:
        add(props, W, "sz", {q(W, "val"): str(size)})
    t = add(r, W, "t", text=text)
    if text.startswith(" ") or text.endswith(" "):
        t.set(q(XML, "space"), "preserve")
    return r


INLINE_RE = re.compile(r"(\*\*.*?\*\*|`.*?`|\*[^*]+\*)")


def write_inline(p, text):
    pos = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > pos:
            set_text_run(p, text[pos:match.start()])
        token = match.group(0)
        if token.startswith("**"):
            set_text_run(p, token[2:-2], bold=True)
        elif token.startswith("`"):
            set_text_run(p, token[1:-1], code=True)
        else:
            set_text_run(p, token[1:-1], italic=True)
        pos = match.end()
    if pos < len(text):
        set_text_run(p, text[pos:])


body = None
paragraph_count = 0
table_count = 0


def p(text="", style="Normal", align=None, keep=False, before=None, after=None, indent=None):
    global paragraph_count
    node = add(body, W, "p")
    paragraph_count += 1
    ppr = add(node, W, "pPr")
    if style:
        add(ppr, W, "pStyle", {q(W, "val"): style})
    if align:
        add(ppr, W, "jc", {q(W, "val"): align})
    if keep:
        add(ppr, W, "keepNext")
    if before is not None or after is not None:
        attrs = {}
        if before is not None:
            attrs[q(W, "before")] = str(before)
        if after is not None:
            attrs[q(W, "after")] = str(after)
        add(ppr, W, "spacing", attrs)
    if indent is not None:
        add(ppr, W, "ind", {q(W, "left"): str(indent)})
    write_inline(node, text)
    return node


def heading(text, level=1):
    return p(text, "Heading%d" % level, keep=True)


def bullet(text):
    return p("•  " + text, "ListParagraph")


def number_item(n, text):
    return p("%s.  %s" % (n, text), "ListParagraph")


def page_break():
    node = add(body, W, "p")
    add(node, W, "pPr")
    r = add(node, W, "r")
    add(r, W, "br", {q(W, "type"): "page"})


def formula(text):
    node = add(body, W, "p")
    ppr = add(node, W, "pPr")
    add(ppr, W, "jc", {q(W, "val"): "center"})
    add(ppr, W, "spacing", {q(W, "before"): "100", q(W, "after"): "100"})
    r = add(node, W, "r")
    rpr = add(r, W, "rPr")
    add(rpr, W, "rFonts", {q(W, "ascii"): "Cambria Math", q(W, "hAnsi"): "Cambria Math"})
    add(rpr, W, "sz", {q(W, "val"): "23"})
    add(r, W, "t", text=text)


def caption(text):
    return p(text, "Caption", keep=True)


def table(headers, rows, widths):
    global table_count
    table_count += 1
    assert len(widths) == len(headers), (headers, widths)
    total = sum(widths)
    tbl = add(body, W, "tbl")
    tblpr = add(tbl, W, "tblPr")
    add(tblpr, W, "tblW", {q(W, "w"): str(total), q(W, "type"): "dxa"})
    add(tblpr, W, "tblLayout", {q(W, "type"): "fixed"})
    borders = add(tblpr, W, "tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        add(borders, W, edge, {q(W, "val"): "single", q(W, "sz"): "4", q(W, "space"): "0", q(W, "color"): "B7C9D6"})
    margins = add(tblpr, W, "tblCellMar")
    for edge, value in (("top", "70"), ("start", "90"), ("bottom", "70"), ("end", "90")):
        add(margins, W, edge, {q(W, "w"): value, q(W, "type"): "dxa"})
    grid = add(tbl, W, "tblGrid")
    for width in widths:
        add(grid, W, "gridCol", {q(W, "w"): str(width)})
    all_rows = [headers] + list(rows)
    for ri, rowdata in enumerate(all_rows):
        assert len(rowdata) == len(headers), (ri, len(rowdata), len(headers))
        tr = add(tbl, W, "tr")
        trpr = add(tr, W, "trPr")
        add(trpr, W, "cantSplit")
        if ri == 0:
            add(trpr, W, "tblHeader", {q(W, "val"): "true"})
        for ci, value in enumerate(rowdata):
            tc = add(tr, W, "tc")
            tcpr = add(tc, W, "tcPr")
            add(tcpr, W, "tcW", {q(W, "w"): str(widths[ci]), q(W, "type"): "dxa"})
            add(tcpr, W, "vAlign", {q(W, "val"): "center"})
            fill = "1F4E78" if ri == 0 else ("F2F6F9" if ri % 2 == 0 else "FFFFFF")
            add(tcpr, W, "shd", {q(W, "fill"): fill, q(W, "val"): "clear"})
            para = add(tc, W, "p")
            ppr = add(para, W, "pPr")
            add(ppr, W, "pStyle", {q(W, "val"): "TableText"})
            if ri == 0:
                write_inline(para, str(value))
                for r in para.findall(q(W, "r")):
                    rpr = r.find(q(W, "rPr"))
                    if rpr is None:
                        rpr = ET.Element(q(W, "rPr"))
                        r.insert(0, rpr)
                    add(rpr, W, "b")
                    add(rpr, W, "color", {q(W, "val"): "FFFFFF"})
            else:
                write_inline(para, str(value))
    return tbl


# Article flow: each block is authored here and assembled into the WordprocessingML document.
blocks = []

def H(text, level=1): blocks.append(("h", text, level))
def P(text): blocks.append(("p", text))
def B(text): blocks.append(("b", text))
def N(num, text): blocks.append(("n", num, text))
def F(text): blocks.append(("f", text))
def C(text): blocks.append(("c", text))
def T(headers, rows, widths): blocks.append(("t", headers, rows, widths))
def PB(): blocks.append(("pb",))

# Cover page
blocks += [("title", "Can a General-Purpose AI Develop a Financial-Prediction System? A Retrospective Case Study of Demand Zone AI"),
           ("subtitle", "AI-assisted system development, evidence boundaries, and a foundation for further research"),
           ("covernote", "Retrospective project-level research manuscript  |  30 September 2026"),
           ("covernote", "Author and institutional affiliation are not recorded in the preserved project materials and are therefore omitted rather than inferred."),
           ("covernote", "This manuscript was prepared with general-purpose AI assistance under the project author's direction. It is not investment advice and does not claim demonstrated predictive efficacy or profitability."),
           ("pb",)]

H("Abstract", 1)
P("This retrospective case study asks to what extent a general-purpose AI can autonomously develop a machine-learning system for short-term financial-market prediction, and whether Demand Zone AI provides a promising foundation for further research. The project author confirms that a general-purpose AI assistant was used to build the model and related project components. The available record supports substantial AI-assisted implementation and analysis within a human-directed process, but does not establish autonomous end-to-end development: the author set the goal, supplied direction, and reviewed or redirected the work, while a complete contemporaneous prompt, tool-use, and authorship log is unavailable. The resulting project includes a rule-based demand-zone system, multiple historical model/dataset versions, a retained v1.0.1 archive, and a frozen v1.0.2 future protocol. A bounded read-only audit verified manifest hash agreement for 153 cached source CSVs, both primary result tables, and all eight saved model artifacts; it checked 61,045 event/label rows, 41,221 unique finite out-of-fold (OOF) score rows, and OOF/event/label consistency. Pooled and fold-level point metrics recalculated from retained scores matched the archive to documented precision. Recalculated pooled OOF AUC contrasts were LightGBM A minus Logistic Regression A = +0.081757 and LightGBM C minus LightGBM B = +0.005688. These are comparisons of retained scores, not reproduction of feature generation, model fitting, or prediction generation. Exact historical source is unavailable, feature parity failed, all 480 aligned AAL rows differed for each of three scoped features, and none of the seven archived bootstrap bounds was reproduced by the current reconstruction. V1–V7 results and the negative V2 simulation remain historical reports, not matched reruns. The v1.0.2 protocol has not been executed; no prospective outcomes exist. We conclude that, according to the project author's account, AI enabled meaningful prototype development under human supervision and that the artifacts offer a promising but incomplete foundation for further methodological research—not evidence that the predictor works or is profitable.")
P("**Keywords:** financial machine learning; demand zones; market structure; reproducibility; look-ahead bias; out-of-fold predictions; retrospective audit")

H("1. Introduction", 1)
H("1.1 Motivation and problem", 2)
P("General-purpose AI assistants can write code, explain methods, inspect artifacts, and help orchestrate experiments. These capabilities raise a practical research question: can a person use such a system to build a domain-specific machine-learning prototype with enough independence to count as autonomous development, and is the result useful for subsequent research? A financial-prediction project is a demanding test case because an operational-looking pipeline can be built more quickly than its evidence can be validated. Daily returns are noisy; relationships vary over time; event samples are selected; and features, targets, or validation procedures can inadvertently use information unavailable at prediction time. A retrospective score may reflect signal, target design, selection, or leakage; it cannot establish AI capability or market efficacy without a traceable development process and reproducible, point-in-time evidence.")
P("Demand Zone AI was developed around a technical-analysis concept: a demand zone is a price region treated as a possible area of support after a prior swing low and subsequent price departure. The software converts this qualitative idea into heuristics for pivots, retests, zone geometry, and technical indicators. A machine-learning question follows: among the occasions selected by those heuristics, do the available predictors rank subsequent outcomes differently? That question is narrower than whether a trading strategy works. AUC measures ordering of positive and negative cases, not a tradable net return, causal support effect, calibrated probability, or all-market opportunity.")
H("1.2 Research question", 2)
P("The central research question is: **To what extent can a general-purpose AI autonomously develop a machine-learning system for short-term financial market prediction, and can the resulting system provide a promising foundation for further research?** The study treats this as two linked but distinct questions. The first concerns the development process: what work the AI assistant performed, what decisions and controls remained human-led, and whether the evidence supports a claim of autonomous end-to-end development. The second concerns the resulting artifact: whether Demand Zone AI provides a sufficiently documented and methodologically useful starting point for further research, separate from whether its predictions are effective.")
P("Three subsidiary questions guide the retrospective: (1) what components and model iterations were produced in the human–AI development process; (2) what parts of the saved v1.0.1 evidence can be verified or recalculated without reproducing the original pipeline; and (3) what technical, provenance, and evaluation gaps must be resolved before the system can support stronger research claims?")
H("1.3 Contributions and scope", 2)
P("The paper contributes a qualitative, evidence-bounded assessment of AI autonomy in one project; a provenance-aware chronology of the V1–V7 model series and separate V10–V13 dataset augmentation series; a bounded verification of archive hashes, row identity, labels, saved OOF scores, and point metrics; and a claim-to-source evidence matrix. It distinguishes development capability from empirical validity: producing working code and a complex artifact is evidence of engineering assistance, not proof of predictive skill. It does not estimate a numeric share of performance attributable to leakage, compare unlike historical targets as controlled arms, or treat a protocol specification as an experiment. Every substantive claim is classified as verified, recalculated, historical/reported, reconstructed but unmatched, or not verified/unavailable.")
H("1.4 Operational definitions and assessment approach", 2)
P("In this case study, **autonomous development** means carrying a system from problem framing through implementation, data preparation, model experimentation, evaluation, and documentation with limited human intervention and independently chosen decisions. **AI-assisted development** means that the AI performs meaningful implementation or analysis tasks while a human sets the objective, supplies constraints, reviews outputs, or redirects work. These are qualitative operational definitions, not a standardized autonomy benchmark. The assessment separates task execution from decision authority: the AI may implement a requested component without independently selecting the research question, accepting its validity, or deciding that evidence is sufficient.")
P("The evidence base is deliberately modest. The project author reports using a general-purpose AI assistant to make the model and related project components; the project artifacts document that a substantial technical system and research archive exist. The available materials do not include a complete contemporaneous prompt/tool transcript, per-file authorship ledger, controlled human-only comparison, time/cost comparison, or repeated trials across AI systems. Accordingly, this paper can describe the project as human-directed, AI-assisted development and assess the resulting artifact, but cannot calculate an autonomy percentage or generalize to general-purpose AI systems as a class. The archive audit separately assesses saved research outputs; it is not an experiment measuring AI autonomy. The archive closeout was a local read-only audit, not an external third-party replication: a hash match establishes file identity against the manifest, not data validity or the process that generated saved scores.")
H("1.5 Related literature", 2)
P("Prior research provides methodological context, not validation of Demand Zone AI. Gu, Kelly, and Xiu [1] study machine-learning approaches to empirical asset pricing, illustrating that model comparisons depend on the prediction target and evaluation design. Sullivan, Timmermann, and White [2] address data-snooping in technical trading-rule evaluation; Harvey, Liu, and Zhu [3] discuss multiple testing in the search for return predictors; and Bailey et al. [4] develop a framework for assessing backtest overfitting. These works motivate careful treatment of repeated model/feature search, validation reuse, and retrospective strategy claims. They do not establish the validity of this project's archive, data, or model scores.")

H("2. Background and project development", 1)
H("2.1 Demand zones and the original software objective", 2)
P("The early project described a pipeline that reads daily open-high-low-close-volume (OHLCV) histories, identifies swing-low regions, counts touches, emits candidate retests, calculates price, momentum, trend, volume, volatility, zone, and candlestick features, and simulates a future trade outcome. In the inspected generator, a pivot is recognized using bars on both sides and made available at a later confirmation bar; candidate touches use a 3% tolerance and are limited per zone. These are algorithmic definitions of a technical pattern, not a validated economic mechanism. The event sample is conditional on the generator finding a candidate and cannot be interpreted as a sample of every stock on every date.")
P("The original README frames the product as an automated demand-zone trading system, including a 20-session simulation with a +15% target. The inspected Python generator's configuration uses a 20-day horizon, +15% target, and −5% stop; a separate README description gives a −7% stop, while another setup example gives −5%. The README initially describes $1–$10 price and minimum-volume filters, whereas the inspected generator configuration sets those filters to None and says it uses a broader market. These differences document evolving configuration, not one stable, fully locked original experiment. Barrier labels also require an explicit convention when daily high and low cross both thresholds on the same candle; the inspected simulator checks the target before the stop.")
H("2.2 V1–V7 model chronology", 2)
P("V1–V7 are the successive training/model records described in available project reports and metadata. They changed targets, features, estimator families, selection steps, validation procedures, and data snapshots. The values below are transcribed as historical reports/metadata unless a cell explicitly says it was recalculated from the saved v1.0.1 OOF predictions. No V1–V7 run was matched end to end during this audit.")
C("Table 1. V1–V7 chronology and reported metrics. All metric cells are historical report/metadata, not independently reproduced results.")
T(["Version", "Documented change / target", "Historical reported result", "Evidence status and comparability"], [
    ["V1", "Baseline cited later as XGBoost, hold1 outcome, 50 features.", "AUC 0.619; top-5% hit rate 29.0% (quoted in the V2 report).", "Historical value quoted by V2; original V1 run artifacts/splits were not recovered. Not an audited baseline."],
    ["V2", "Expanded to market/regime, relative-strength, volatility, liquidity, event and other features; several estimators and targets; 120 features for reported best CatBoost; 5-fold walk-forward reported.", "44,854 rows, 149 tickers, 2021-08-03–2026-06-24. CatBoost hold1 report: mean AUC 0.675950, SD 0.022838. Reported simulation: 1,228 trades, 47.6% wins, −0.04% average/trade, PF 0.97, Sharpe −0.16, PnL −$9.77.", "Report only; no matched rerun. Backtest was not independently reproduced and its implementation needs review. Different pipeline from V1."],
    ["V3", "Adds SPY-relative targets and additional features, including gaps/open-drive and market context.", "Metadata: five-fold alpha_spy_2pct AUC 0.728106; hold1_2pct AUC 0.671232; alpha_spy_1pct AUC 0.710673.", "Historical metadata only. Targets differ; forward benchmark-return predictors remain a source-level concern."],
    ["V4", "Ensemble and interactions; recency weights; ticker/month outcome-derived encoding.", "alpha_spy_2pct OOF AUC 0.744640; reported test AUC 0.727987; top-5 hit rate 53.49%.", "Historical metadata. Outcome-encoding and validation-reuse concerns; not a matched comparison with V3."],
    ["V5", "Adds sector/VIX context, zone features, interactions and ensemble; broadens target menu.", "Selected alpha_spy_3pct: OOF AUC 0.784078; reported test AUC 0.752945; top-5 43.13%; base rate 11.85%.", "Historical metadata; different and less common target than V4. Not an apples-to-apples improvement."],
    ["V6", "Magnitude and same-day movement experiments on an expanded feature set.", "Metadata: magnitude AUC 0.725831; same-day absolute-move AUC 0.760557.", "Historical metadata; distinct outcomes, not a continuation of the same hold1 target."],
    ["V7", "Equal-weight tree ensemble, chronological folds and broader exclusions; OOF features selected by first training-fold variance; final saved-model features selected using full-dataset variance.", "Metadata: 3-fold OOF AUC 0.7084 for hold1_2pct, 0.7049 for alpha_spy_2pct, 0.6989 for magnitude.", "Historical metadata only. Full-data variance selection applies to the final saved fit, not by itself the archived OOF scores; no matched rerun or prospective evidence."],
], [760, 2450, 3200, 2950])
P("These numbers must not be read as a rising or falling performance series. V2's hold1 result, V3–V5 alpha targets, V6 magnitude/same-day tasks, and V7's several targets ask different questions. Data, candidate rows, features, fold construction, selection, metrics, and thresholds also changed. Even two numbers with the same target name can be affected by a changed dataset or selection process. There is no controlled estimate of a version-to-version improvement or a leakage-adjusted historical performance.")
H("2.3 Separate V10–V13 dataset augmentation history", 2)
P("The V10–V13 labels are a separate dataset-generation/augmentation lineage, not later model versions in the V1–V7 controlled model sequence. They add columns and heuristic labels to a barrier-labeled dataset. Their outputs must not be described as a controlled performance progression, and the proxy labels must not be mistaken for realized barrier outcomes.")
C("Table 2. V10–V13 dataset lineage as documented in the retained augmentation scripts.")
T(["Dataset stage", "Documented operation", "Interpretive limitation"], [
    ["V10", "Rule-based demand-zone event dataset and 20-session forward simulation; +15% target and −5% stop in the inspected generator configuration, plus excursion/outcome columns.", "Daily OHLC bars cannot order same-session target/stop touches without a convention; inspected code checks target first. README variants also differ on stop configuration."],
    ["V11", "Adds derived zone/market/volume features; sets market_relative_hit equal to hit_target.", "The copied label is a proxy, not a realized comparison against a market return."],
    ["V12", "Adds strong_hit = hit_target and SPY 20-day return > −1%, plus derived features.", "A transformed label with a market-condition filter, not an independently observed market-relative trade outcome."],
    ["V13", "Adds heuristic hit_5pct/hit_10pct/hit_20pct, target_tier, expected-return proxies, regime and structure features; hit_15pct copies hit_target.", "Several thresholds are feature-rule proxies rather than direct observations that the corresponding return barrier was reached. No comparable V10–V13 model result series was recovered."],
], [1100, 4650, 3610])
P("A later hold1 target builder reconstructs open-to-open returns from downloaded OHLCV for V13 rows, but its implementation has weaker validity checks than the frozen protocol: target comparisons are materialized before a final missing-return filter, and finite positive forward-open checks are not as explicit as the v1.0.2 rule. The script subsequently drops missing hold1_ret rows, so this audit does not assert that missing rows survived into a particular saved training table. The concern is that validity depends on downstream filtering and data quality, which need to be checked for each version rather than inferred from a function name.")

H("3. Data and experimental development", 1)
H("3.1 Datasets and population", 2)
P("The V2 report describes a dataset of 44,854 rows, 149 tickers, and signal dates from 2021-08-03 through 2026-06-24. The v1.0.1 archive is separate: its development report and manifest describe 61,045 candidate events and mature labels on a recovered fixed 149-symbol roster, with event signal dates from 2021-08-03 through 2025-12-31. The source cache has 153 files: the 149 roster symbols plus SPY, QQQ, IWM, and VIX (stored as XVIX.csv), with cached history through 2026-08-03 in the archive manifest. The audit verified the cached source CSV file hashes against the v1.0.1 manifest; it did not verify historical vendor vintages, price adjustments as originally known, or the historical membership of the universe.")
P("The roster is a recovered fixed project list. Its original selection date, point-in-time constituent membership, treatment of delisted issuers, and survivorship properties are unavailable. Local OHLCV is Yahoo-derived, auto-adjusted historical data; current cached values do not constitute point-in-time data vintages. The archive's hash pass establishes that the files match recorded digests, not that those files represent contemporaneously available prices. All historical interpretations are conditional on this project roster and event generator.")
H("3.2 Targets and labels", 2)
P("The v1.0.1 report identifies a one-session open-to-open target: for signal date T, entry is Open[T+1], exit is Open[T+2], and the binary label is positive when the resulting return is at least 2%. The audit checked the retained event labels against the inclusive threshold `hold1_ret >= 0.02`, along with finite OOF scores and aligned saved return/entry/exit fields. For eligible archived rows, the target can be written as:")
F("R(T) = Open(T+2) / Open(T+1) − 1;     Y(T) = 1[R(T) ≥ 0.02].")
P("This verified row-level arithmetic does not prove how historical OHLCV was adjusted or that the original source generated the event/feature table identically. Earlier versions also used 20-day target/stop simulations, SPY/sector-relative targets, triple-barrier labels, magnitude outcomes, same-day movement labels, and heuristic proxies. Those are not interchangeable endpoints. The frozen v1.0.2 protocol explicitly requires finite, strictly positive Open[T+1] and Open[T+2], finite return, and filtering before binarization; that is a future design constraint, not an assertion that every legacy builder enforced it.")
H("3.3 Features and model families", 2)
P("The v1.0.1 report describes four nested feature arms and two estimator families. Arm A contains 20 price, momentum, and volume features; B adds volatility and market context (38 total); C adds demand-zone geometry and retest-state features (65 total); D adds order-block features (99 total). The eight model/arm combinations are Logistic Regression A–D and LightGBM A–D. The audit verified saved score columns and event identity; it did not independently establish that the original code produced the claimed feature values or trained those model objects with the stated settings.")
P("Legacy V2–V7 feature sets include moving averages, momentum, volume, zone geometry, market/sector context, volatility, gaps, interactions, and, in some versions, recency weighting and target encodings. Their precise feature matrices are not recoverable as matched, per-version run bundles. Historical metadata may enumerate a feature list, but a list does not establish that every feature was point-in-time valid or was computed using the same transformation at training and prediction time.")
H("3.4 Historical evaluation and retained OOF structure", 2)
P("The v1.0.1 archive report describes chronological annual validation folds for 2023, 2024, and 2025. It retains 41,221 unique OOF-scored events: 13,924 in 2023, 13,180 in 2024, and 14,117 in 2025. The remaining 19,824 labeled event rows are not in those OOF score sets. Signal dates in the saved scored rows range from 2023-01-03 to 2025-12-31, prior to the exclusive 2026-01-01 cutoff recorded in the archive closeout. The audit verified OOF/event/label alignment and recalculated point metrics from those retained scores. It did not refit any fold or confirm source-level fold construction.")
P("The archived report/manifest describes training rows as chronologically separated and purged by label maturity. Since the exact source hash is unavailable and no historical fold was refit, that description is attributable to the archive record rather than an independently reproduced training procedure. For V1–V7, split schemes varied and are reported only where retained reports/metadata specify them. A chronological split alone would not cure future-valued features or repeated reuse of validation outcomes.")

H("3.5 Human–AI development process and autonomy assessment", 2)
P("The project is examined as a single human–AI development case, not as a controlled benchmark of AI agents. The project author confirms that a general-purpose AI assistant was used to build the model and related work; this statement is a retrospective disclosure made during this manuscript preparation. In the collaboration represented here, the user supplied the goal—developing a short-term financial prediction system—and later clarified the intended research question and evidentiary standards. The AI assistant contributed implementation and analysis work under those instructions, including working with project code and artifacts; the available repository contains the resulting model-development history, audit materials, a frozen protocol, and this manuscript. This description attributes the collaboration at the project level only: there is no complete contemporaneous prompt/tool log or file-level authorship record, so the evidence does not permit reliable allocation of individual files, decisions, or historical metrics between human and AI authorship.")
C("Table 2A. Qualitative assessment of autonomy across development stages.")
T(["Stage", "What the retained record supports", "Assessment", "Boundary"], [
    ["Problem framing", "The user states the project goal and directs the research question; the user corrected the paper's initial framing.", "Human-led; AI responsive.", "No evidence the AI independently selected this financial prediction problem."],
    ["Implementation", "The project author reports using the AI assistant to make the model and related components; a substantial code/model artifact set exists.", "Meaningful AI-assisted development.", "No complete prompt history or per-file provenance to quantify contribution or verify independent task completion."],
    ["Experiment design and iteration", "Multiple targets, feature sets, estimators, and versions are present; the current frozen protocol specifies a more controlled future design.", "Collaborative / incompletely attributed.", "No complete decision log showing which choices were independently proposed or made by AI versus human."],
    ["Execution and evaluation", "The retained archive was audited and its saved-score point metrics recalculated; the historical source pipeline was not reproduced.", "AI-supported, human-directed review.", "Archive checks are not a measure of autonomous research judgment or a matched model rerun."],
    ["Scientific governance", "The user explicitly required cautious claims, evidence categories, and a standalone deliverable; the frozen protocol is not executed.", "Human oversight is material.", "No basis to claim the AI independently determined when evidence was adequate or authorized prospective testing."],
], [1500, 3000, 2100, 3300])
P("The defensible autonomy conclusion is therefore bounded: this case demonstrates that a general-purpose AI can contribute substantially to implementation and research-support work when directed by a human, but it does not demonstrate independent, end-to-end autonomous development. In particular, the existence of a sophisticated system and historical metrics cannot establish that the AI independently designed a sound experiment or recognized all validity problems. The archive audit and the user's corrections illustrate a complementary role for human oversight: defining the question, challenging framing, and setting the standard for claims.")

H("4. Reproducibility and audit method", 1)
H("4.1 Evidence hierarchy", 2)
P("The audit uses five evidence labels. **Verified by audit** means the stated property was checked against retained files within the scope recorded in the closeout. **Recalculated from retained predictions** means the statistic was recomputed from saved OOF labels and score columns, without reconstructing upstream features or fitting a model. **Historical reported result** means a value appears in a project report or model metadata but was not matched by this audit. **Reconstructed but not matched** means current editable code or a source-prefix comparison was examined, but did not reproduce the archived source/features/results. **Not verified / unavailable** means that necessary original files, provenance, incident details, or an executed experiment are absent. These categories are not interchangeable.")
H("4.2 Archive identity and integrity checks", 2)
P("The read-only closeout compared retained archive hashes to the v1.0.1 run manifest. It reported a pass for 153/153 cached source CSVs, both primary result tables, and all eight saved model artifacts. The manifest-recorded SHA-256 digests for the two primary tables are: `event_table.csv` 232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0; and `oof_predictions.csv` 011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829. The manifest records historical code SHA-256 29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b and protocol SHA-256 486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07. No intact Python source matching the historical code digest was recovered.")
P("A hash match is an identity and mutation-detection result relative to a manifest. It is not a source audit, a proof that cached prices were contemporaneously available, a verification of the model-fitting process, or a third-party endorsement of the model. Model files can be preserved exactly even when the code that created them is not.")
H("4.3 Event, label, and OOF consistency", 2)
P("The closeout reports 61,045 event rows and labels, 41,221 unique OOF rows, and 19,824 labeled rows outside the OOF predictions. It checked that OOF event identifiers, labels, returns, entry dates, and exit dates align with the event table; that saved OOF scores are finite; that labels agree with the inclusive 2% hold1 rule; and that saved forward dates mature after signal date. It also checked the expected validation-year counts and the strict pre-2026 signal-date cutoff. These are checks on saved tables, not a replay of pivot detection, feature calculation, or model inference.")
H("4.4 Point metrics and reconstruction boundary", 2)
P("Pooled and fold-level point metrics were recalculated from retained OOF score columns and matched the manifest; pooled values match the archived development report to its displayed precision. The two primary paired point AUC differences also recalculate from those saved predictions. No feature generation or model fitting was performed during the closeout. The audit utility is intentionally read-only and, in its default form, does not regenerate features, run the historical pipeline, fit models, run the bootstrap, or create prospective predictions.")
P("The available reconstruction matched archived event counts and ordered event IDs in a source-prefix comparison, but multiple feature values did not match. In a scoped AAL comparison, all 480 aligned AAL rows differed for each of `rsi14`, `atr_pct`, and `zone_width_pct`. This is direct evidence that the reconstruction is not feature-equivalent in the tested scope. It is not a full replay and does not identify the cause of every difference.")
H("4.5 Bootstrap and bytecode boundaries", 2)
P("The archived v1.0.1 report/manifest contains seven interval bounds for paired AUC contrasts. A prior full calculation using the current reconstructed weekly block-bootstrap helper failed to reproduce any of those seven bounds; point contrasts and valid-resample counts matched. The cause is unknown; the closeout did not rerun the bootstrap. Accordingly, the manuscript treats interval bounds as copied historical values only. It does not substitute newly generated bounds or claim independent confidence-interval reproduction.")
P("An older Python 3.13 bytecode file used in a bounded replay was explicitly unreviewed and is not source-equivalence evidence. Its prior recorded digest was c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585. A later `py_compile` overwrote the cache path; the current cache digest is ee9017b7cf354931d638cb83bdc276c341bad9e90278addcdeec9ba60b4a7ed6, and no trusted copy with the former digest was found. The earlier replay cannot be used to claim reproduction.")

H("5. Results", 1)
H("5.1 A. Independently checked archive findings", 2)
P("The verified result is narrow but useful: the preserved v1.0.1 archive is internally consistent at the saved-file identity, event/label/OOF alignment, and saved-score point-metric levels examined. The pooled model scores below are retained OOF results; their point statistics were recalculated from the score columns. They are not results from a recovered source rerun, do not verify feature construction, and are not prospective outcomes.")
C("Table 3. Pooled v1.0.1 OOF point metrics recalculated from retained score columns; rounded as in the archive report. All rows use 41,221 saved OOF events and a 16.48% OOF positive rate.")
T(["Estimator / arm", "Events", "Positive rate", "Pooled ROC-AUC", "Average precision", "Mean daily AUC¹", "Top-5% precision / same-date base"], [
    ["Logistic Regression A", "41,221", "16.48%", "0.5901", "0.2324", "0.5883", "28.35% / 16.12%"],
    ["Logistic Regression B", "41,221", "16.48%", "0.6608", "0.2688", "0.6815", "32.57% / 16.12%"],
    ["Logistic Regression C", "41,221", "16.48%", "0.6603", "0.2663", "0.6752", "32.52% / 16.12%"],
    ["Logistic Regression D", "41,221", "16.48%", "0.6596", "0.2655", "0.6732", "31.68% / 16.12%"],
    ["LightGBM A", "41,221", "16.48%", "0.6718", "0.2610", "0.6692", "30.10% / 16.12%"],
    ["LightGBM B", "41,221", "16.48%", "0.6778", "0.2739", "0.6931", "30.70% / 16.12%"],
    ["LightGBM C", "41,221", "16.48%", "0.6835", "0.2768", "0.6940", "30.95% / 16.12%"],
    ["LightGBM D", "41,221", "16.48%", "0.6848", "0.2748", "0.6944", "30.90% / 16.12%"],
], [1900, 830, 900, 1250, 1250, 1450, 1780])
P("¹Mean daily AUC is the equal-weight mean across dates with both classes; the archive report lists 728 such dates. Top-5% precision is conditional on that date's emitted candidate-event set and is shown beside the same-date base rate. Neither value is a portfolio return or an all-market selection rate.")
H("5.2 Two primary saved-score contrasts", 2)
P("For a paired contrast, the same saved event rows and labels are used for both score columns, and the reported delta is the difference in pooled OOF ROC-AUC. The audit recalculated these point differences directly from the retained predictions:")
F("Δ(AUC) = AUC(score model 1, retained OOF labels) − AUC(score model 2, retained OOF labels).")
C("Table 4. Primary paired contrasts: point differences recalculated; intervals copied from the archive and not reproduced.")
T(["Saved-score contrast", "Recalculated Δ AUC", "Archive-reported 95% interval", "Interpretation boundary"], [
    ["LightGBM A − Logistic Regression A", "+0.0817570837 (≈ +0.081757)", "[0.0657508832, 0.0990268148]", "Difference between retained baseline-arm scores; not a refit, calibration result, causal effect, or future forecast."],
    ["LightGBM C − LightGBM B", "+0.0056875596 (≈ +0.005688)", "[0.0021785160, 0.0091912802]", "Difference between retained C and B scores; cannot be confidently attributed to intended zone features because feature parity failed. Interval is not verified."],
], [2200, 1900, 2300, 2960])
P("The first contrast is an archived-score comparison of two estimator columns in baseline arm A. The second compares archived LightGBM score columns for feature arms C and B. The second point estimate is numerically small relative to AUC's [0,1] scale. Neither difference establishes that a model family is generally superior or that the market-structure block causes an improvement. The archived interval values are not fresh confidence intervals: the bootstrap mismatch remains unresolved. AUC deltas alone say nothing about transaction costs, position sizing, calibration, net profitability, or generalization to future markets.")
H("5.3 B. Historical reported V1–V7 findings", 2)
P("Table 1 records the available historical reports/metadata. Their values are explicitly not elevated to audit-verified results. The V2 simulation's negative summary is noteworthy because it does not support the report's most optimistic production-readiness language: the V2 report records a negative average trade return, a profit factor below one, a negative Sharpe ratio, and negative total PnL. The archive audit did not independently reproduce this simulation, validate its trade accounting, or establish that its assumptions match an executable strategy. It should be described as a historical negative simulation report, not as a confirmed loss estimate or an independently tested profitability result.")
P("Likewise, V2's reported calibration statistics, V3–V7 AUCs and top-k rates, and V1's quoted baseline remain report-level evidence. This paper does not claim reliable calibration, nor does it claim that the V1–V7 metrics were independently confirmed. Their numerical differences cannot be interpreted as a clean performance trajectory because target definitions, base rates, features, training rows, fold design, and model-selection choices changed.")
H("5.4 C. Reconstruction discrepancies and unavailable reproduction", 2)
P("The exact historical v1.0.1 source file matching the manifest code digest was not recovered; the partial source is damaged. The current source is a reconstruction, not the original run source. The prefix comparison aligned event counts and ordered IDs but failed feature parity. The scoped AAL comparison found all 480 aligned AAL rows different for each of `rsi14`, `atr_pct`, and `zone_width_pct`. Thus the archive's scores can be checked arithmetically but cannot be attributed confidently to reconstructed inputs or the intended feature blocks.")
P("None of the seven archived bootstrap bounds was reproduced by the reconstruction helper; the cause remains unknown. The old bytecode replay was unreviewed and the cache was overwritten; it is excluded as reproduction evidence. V1–V7 have not been matched through end-to-end reruns. The V2 trading simulation is not independently confirmed. These are substantive reproducibility limits, not administrative details.")
H("5.5 D. What the case shows about AI autonomy and research potential", 2)
P("The project author reports using a general-purpose AI assistant to develop the model and related system work, and the preserved project contains multiple training/data iterations, a scored historical archive, a read-only integrity audit, and a frozen future protocol. This supports a positive but limited capability finding: AI can help a human assemble a technically substantial financial-ML prototype and can assist with later audit and documentation. The process evidence does not support describing Demand Zone AI as autonomously developed in the strong sense of an AI independently defining the question, sourcing and validating point-in-time data, choosing a sound design, executing a faithful reproduction, and deciding whether the evidence warrants a claim. Human direction and review remained material, and complete process logs are unavailable.")
P("As a foundation for further research, the system is promising in the methodological and engineering sense: it preserves a nontrivial development history, eight model artifacts and saved OOF scores, a hash-checked archive, explicit limitations, and a frozen protocol that constrains a future comparison. It is incomplete as an empirical foundation because historical code and feature parity are missing, all seven archived bootstrap intervals remain unreproduced, legacy runs are unmatched, and prospective evaluation has not begun. Thus the answer to the research question is conditional: general-purpose AI demonstrated useful, human-supervised development capacity in this project; Demand Zone AI is a promising starting point for a more rigorous study, but neither autonomous end-to-end research capability nor short-term predictive effectiveness is established.")

H("6. Methodological findings", 1)
H("6.1 Feature availability and forward-information risk", 2)
P("A feature is eligible for prediction only if its inputs were observable by the signal timestamp. In the inspected V2 dataset builder, benchmark columns such as `bench_XLK_hold1` are constructed from a future benchmark open relative to the feature date. The V2 trainer's exclusion list removes `bench_SPY_hold1` but does not exclude the whole family of benchmark hold1 columns. The V2 report lists `bench_XLK_hold1` among its top ten permutation-importance features. Together these files document a concrete forward-information risk in the legacy pipeline. This code/report review does not quantify how much the risk affected any AUC, and the V2 model was not rerun to estimate a corrected score. V3–V5 feature records also include multiple benchmark hold1 fields, so the concern is not limited to one version.")
P("Other older pipelines contain outcome-derived predictors or selection choices that require caution. V4 code constructs ticker hit-rate features sequentially, but its month hit-rate is computed from all outcomes within each calendar month, including outcomes later than an individual row in that month; this is a time-ordering risk. V5 code also computes month- and sector-level hit rates from broad target aggregates. V4–V5 training material describes ensemble weights informed by fold AUC. V2's feature-audit stage computes target-related feature screening before its folds. V7's OOF feature indices are selected using variance in the first training fold and reused; separately, the final saved model's feature selection recomputes variance over the full dataset. The latter includes historical evaluation-period feature distribution in final-model selection, but by itself does not show that the reported OOF predictions used future-fold variance. These source-level observations are methodological risks; the exact effect on any reported score is unavailable, and no numeric leakage fraction is claimed.")
H("6.2 Labels, event timing, and barrier simulation", 2)
P("The project moved among barrier-touch, hold1, benchmark-relative, magnitude, and heuristic-proxy outcomes. Barrier simulation on daily bars cannot determine intraday ordering when both stop and target are touched without a stated convention. In the inspected early generator, the target check precedes the stop check. This favors the target when both are touched on the same day under that implementation. Later V11–V13 augmentation scripts create proxy labels from current features and previously assigned labels; those columns are not substitutes for market-observed barrier returns.")
P("The historical hold1 target builder forms threshold indicators before dropping rows with missing hold1 returns. Its final output path does drop missing hold1_ret rows, but the binary comparisons themselves can turn missing comparisons into zeros if downstream filtering is omitted or changed. It also does not enforce every finite, positive-forward-open condition required by v1.0.2. This is a code-level reason to make label eligibility explicit before binarization; it is not evidence that the audited archive labels were wrong, because the saved archive consistency check found that its retained labels match its saved returns and threshold.")
H("6.3 Validation reuse, calibration, and selection", 2)
P("Chronological splits do not by themselves protect against forward-valued columns, target-derived transformations computed before the split, label windows crossing validation boundaries, or repeated selection on the same dates. Legacy trainers and reports document changes to targets, features, weights, ensembles, encodings, and cutoffs over many iterations. Once a validation result influences a subsequent design decision, the period is development data rather than untouched confirmation. The project does not retain sufficient matched run bundles to quantify this selection history.")
P("V2 reported Platt and isotonic calibration summaries. Its training code fits calibrators using the OOF rows and evaluates calibration statistics on rows used in that fitting workflow, with a non-chronological two-fold calibration split over the collected OOF matrix. Those report values are not revalidated here and do not demonstrate reliable calibration. No calibration study was performed for the retained v1.0.1 point-score audit or for v1.0.2, which has not run.")
H("6.4 NKE leakage episode: limited provenance", 2)
P("A project-author recollection reports an episode involving leakage associated with NKE. The retained materials do not establish the exact feature, affected date range, mechanism, discovery artifact, before/after run, or performance effect for that episode. It must therefore be presented as a reported incident, not an independently verified finding. The account is consistent with why point-in-time checks matter, but it cannot support a precise causal diagnosis or quantify any change in historical results. The missing supporting incident detail is listed in the evidence matrix.")
H("6.5 Backtest and market-data provenance", 2)
P("The V2 report calls its simulation an honest backtest and provides negative summary statistics, but the archive audit did not reproduce the code path or trade ledger. The inspected implementation has position-accounting and timing logic that warrants review before any result is interpreted as a strategy return; the paper therefore does not affirm its assumptions, transaction-cost implementation, or exact trade count. This caution does not reverse the reported negative direction; it limits what can be concluded from that report.")
P("The fixed 149-name roster and current Yahoo-derived adjusted histories lack point-in-time constituent and vintage provenance. Corporate-action back-adjustments and vendor corrections may differ from values available at a historical date. File hashes preserve the snapshot used in the archived manifest, but do not establish a tradable, historical information set. This precludes broad-market or point-in-time-universe claims.")
H("6.6 Bootstrap interval mismatch", 2)
P("The seven archived interval bounds remain unverified by the current bootstrap implementation. The point AUC differences can be recalculated from archived scores even though interval construction cannot. The interval mismatch has no known root cause; no replacement bounds are presented. The paper distinguishes the interval numbers in Table 4 as archive-reported and keeps them out of the verified/recalculated evidence category. Any future analysis would need an exact, version-matched uncertainty implementation and a separately frozen analysis record.")

H("7. Frozen v1.0.2 protocol for a future experiment", 1)
P("The machine-readable `MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json` is frozen as version 1.0.2 with decision date 2026-09-28. It specifies a future/prospective evaluation design and a retrospective development replay contract. It is not a run manifest, has not been executed as v1.0.2, and produced no scores, intervals, predictions, outcomes, calibration measurements, or profitability results. The v1.0.1 archive is a distinct historical artifact and does not become v1.0.2 through this protocol revision.")
P("The frozen historical development contract excludes all study signal events dated on or after 2026-01-01, although later cached bars may be read only to mature forward labels for signal dates through 2025-12-31. Training labels must have exit_date before each validation start; final development fit rows must also have signal_date and exit_date strictly before 2026-01-01. The local archive cache extends through 2026-08-03, but the 2026 tail is coverage only: it is not a prospective holdout and was not used to create prospective evidence.")
H("7.1 Population, event clock, and label", 2)
P("The protocol conditions the estimand on one candidate demand-zone retest event per ticker-session from the recovered fixed 149-symbol roster. The legacy V2 table is used only to recover roster membership; its old rows, features, and labels are not used to construct the study's events, predictors, or outcomes. A signal is timestamped after close T. A swing low at index i qualifies when Low[i] is no greater than Low[i−1], Low[i−2], Low[i+1], and Low[i+2]; it is not available until the second following bar i+2 has closed. The zone price is Low[i], with width ATR(14)[i]/Close[i]; formation and departure summaries stop at confirmation. A retest is the first bar of a contiguous run whose low is within 3% of the zone price, strictly after confirmation. Each zone can emit at most five retest starts; when several zones qualify for a ticker-date, one is selected by highest known touch count, then smallest absolute close-to-zone distance, then lowest stable chronological zone ID. Inputs are limited to bars dated no later than T and histories must be truncated at an explicit as-of date before prospective feature construction. These are protocol definitions; no claim is made that the historical archive was produced by an exactly matching implementation.")
P("The target is the next ticker-session open-to-open return Open[T+2]/Open[T+1]−1, labeled positive at an inclusive 2% threshold. Rows are excluded from supervised evaluation unless the two forward opens and computed return are finite and strictly positive; the validity mask precedes label conversion. The protocol excludes alpha, barrier, proxy, magnitude, and alternate-threshold targets from its primary study.")
H("7.2 Nested features, estimators, and historical folds", 2)
P("Feature arms are fixed and nested: A uses 20 baseline price/momentum/volume features; B adds 18 volatility/market-context features for 38 total; C adds 27 demand-zone features for 65 total; and D adds 34 order-block features for 99 total. No target encoding, outcome-driven selection, forward benchmark returns, IDs, absolute price levels, or future mitigation/outcome fields are allowed. Missing-value imputation is fit on training rows only; Logistic Regression also uses training-fold standardization. The causal order-block tracker is fixed to a 1% displacement, 0.6 ATR and 0.5 relative-volume threshold, an opposing block of up to three bars, five-bar lookback, 90-calendar-day maximum age, and 100-session warmup. It must update once per closed bar, retain nearest unmitigated bullish and bearish blocks, and exclude higher-timeframe alignment, structure-break flags, and future mitigation outcomes. Event/order-block prefix-invariance tests are required for a conformant future implementation. The original batch detector is not asserted to be prefix invariant, and the reconstructed implementation is not feature-matched to the archive.")
P("The only specified estimators are fixed Logistic Regression and fixed LightGBM, each scored in all four feature arms. Logistic Regression is L2-penalized with C=1, lbfgs solver, 2,000 maximum iterations, random seed 42, and no class weights; its median imputer and standard scaler are fit within the training fold. LightGBM has 300 estimators, max depth 6, 31 leaves, learning rate .03, .8 row and column subsampling, minimum child samples 30, L1 regularization .1, L2 regularization .5, seed 42, one CPU thread, and deterministic/column-wise settings; its median imputer is also training-fold-only. No hyperparameter search, ensemble tuning, threshold selection, calibration, or result-driven model change is permitted. Historical development folds cover validation signal dates in 2023, 2024, and 2025; every training label must mature strictly before its validation start. The final-fit protocol requires both signal_date < 2026-01-01 and exit_date < 2026-01-01. These folds are explicitly retrospective development folds, not untouched confirmation. A constant score with AUC 0.5 is a reference, not another fitted model.")
H("7.3 Planned metrics and prospective controls", 2)
P("The protocol specifies pooled OOF ROC-AUC as its primary retrospective development summary, plus fold AUC, average precision, mean daily AUC on dates with both classes, top-5%-per-date precision beside same-date prevalence, event counts, and positive rates. For paired AUC uncertainty it specifies 1,000 circular moving-block resamples of four consecutive calendar weeks with seed 42; these would be descriptive intervals. Those are future protocol settings only. The v1.0.1 archived interval values are not a successful execution of this v1.0.2 specification.")
P("A prospective phase can begin only after a separately reviewed, hash-consistent implementation, data snapshot, protocol, test suite, and eight fitted development pipelines are locked and an append-only hash-chained prediction/outcome ledger is initialized. The first eligible close must be on a New York trading date strictly after the recorded UTC lock timestamp and after the latest date in the locked source snapshot; no historical signal may be backfilled. Successful no-candidate runs and failures are retained, but only a successfully logged eligible prediction event starts the clock. Each event's feature values, eight scores, as-of provenance, source-prefix hashes, and protocol/code/model hashes must be written before outcomes. Retraining, tuning, threshold changes, or result-dependent early stopping are disallowed. Prediction accrual stops at 2,000 unique events or 18 calendar months, whichever comes first; a single final analysis is permitted only after both at least 12 calendar months and at least 2,000 eligible outcomes have matured. If 2,000 predictions accrue before month 12, prediction stops while the ledger stays sealed until month 12. Any shortfall at month 18 must be reported without extending the window.")
H("7.4 Execution status", 2)
P("No prospective lock or ledger exists in the audit record; there are zero prospective predictions and zero prospective outcomes. No v1.0.2 result table is populated in this paper. A frozen protocol reduces analytic flexibility and creates a checklist for a future study, but freezing design is not evidence that the design was run, that source parity was obtained, or that a future result will be positive.")

H("8. Discussion", 1)
P("The central question concerns both capability and outcome: how autonomously can a general-purpose AI develop a short-term financial prediction system, and does the resulting system support further research? This case indicates that AI assistance can contribute materially to implementation, model development, code and artifact review, and research documentation. It does not show strong autonomy. The project's author supplied the goal and important constraints, corrected the manuscript's framing, and required distinctions between reported and verified evidence. There is no complete development log or comparison against a human-only workflow, so the AI's contribution cannot be quantified and the case cannot support a general claim about AI systems as a class.")
P("The resulting artifacts offer a qualified foundation for subsequent research. A 153-file source cache, immutable v1.0.1 archive, eight saved models, aligned OOF tables, historical version records, and frozen v1.0.2 design provide concrete material to build on. The audit also improves that foundation by exposing boundaries: exact source recovery failed; feature parity was not achieved; archived intervals remain unreproduced; and V1–V7 runs were not matched. A next study would need to rebuild and independently review the pipeline, establish point-in-time data and universe provenance, preserve complete run bundles, and execute a new protocol-compliant prospective evaluation. The present record is useful partly because it identifies what should not be carried forward uncritically.")
P("The 153 source CSV hashes, primary table hashes, and model hashes match the v1.0.1 manifest; saved OOF rows align with archived events and labels; and point metrics and two primary score contrasts can be recalculated. These checks establish selected retained-file identity and arithmetic, not historical feature generation, model fitting, or prediction generation. The +0.005688 LightGBM C−B contrast is not a demonstrated market-structure effect; failed feature parity prevents confident attribution, and historical dates were already part of development. Neither it nor the larger LightGBM-A versus Logistic-A contrast establishes causality, calibration, profitability, or future performance.")
P("The methodological lesson applies both to AI-assisted research and financial ML: technical production and scientific validation are separate capabilities. A system can generate a complex artifact without independently recognizing information leakage, data provenance gaps, validation reuse, or the difference between AUC and trading returns. Human oversight, transparent evidence labels, reproducible code/data, and prospective controls remain essential. A frozen protocol can guide future work but cannot retroactively create a prospective test.")

H("9. Limitations", 1)
P("The retrospective study is limited by missing source and run artifacts, historical iteration and selection, and the restricted scope of its audit. In particular:")
for item in [
    "The exact v1.0.1 Python source corresponding to the manifest code hash is unavailable as an intact file; the remaining partial source is damaged. The editable implementation is a reconstruction, not a source-equivalent replacement.",
    "Feature parity was not achieved. The event-count/order prefix comparison does not repair this; a scoped AAL comparison found all 480 aligned AAL rows differed for each of `rsi14`, `atr_pct`, and `zone_width_pct`. No full feature replay was completed.",
    "The seven archived bootstrap interval bounds were not reproduced. The root cause is unknown, and no replacement interval is presented.",
    "V1–V7 historical metrics were not matched through end-to-end reruns. The reported V2 trading simulation was not independently reproduced; its transaction, timing, and position logic needs review.",
    "The old bytecode replay was explicitly unreviewed, later overwritten at its cache path, and has no trusted matching copy. It cannot be treated as reproduction evidence.",
    "Complete per-version run bundles (exact source, input snapshot, preprocessing, folds, predictions, model hashes, and environment) are missing for the legacy V1–V7 sequence. Some reports or metadata exist, but their availability is uneven.",
    "Point-in-time market data vintages and historical universe membership are unavailable. The fixed 149-symbol roster may contain selection or survivorship bias; cached Yahoo-derived adjustments may include later revisions.",
    "The supporting detail for the reported NKE leakage episode is missing. Its exact feature, dates, mechanism, before/after run, and effect cannot be verified.",
    "The cause of the bootstrap mismatch is unknown. Historical interval bounds therefore remain reported values only.",
    "The archive's dates were historical and had already informed project development. The retrospective folds do not constitute prospective or untouched confirmatory evidence.",
    "V1–V7 targets, feature sets, universes, splits, and model-selection procedures differ. No apples-to-apples version comparison or numeric leakage attribution is possible from current artifacts.",
    "AUC, average precision, and conditional top-k event precision do not establish calibrated probability, causal impact, executable returns, or net profitability. No verified cost-aware strategy evaluation or prospective performance is available.",
    "The v1.0.2 specification is frozen but unexecuted. No predictions, outcomes, uncertainty intervals, or profit measures exist for it.",
    "The AI-autonomy assessment is a single retrospective case based partly on the project author's disclosure during manuscript preparation. No full prompt/tool transcript, contemporaneous contribution ledger, controlled human-only workflow, time/cost benchmark, or replication across AI systems is available; the AI contribution cannot be quantified or generalized.",
]:
    B(item)
P("These limitations are part of the result. They are not repaired by rounding reported numbers, selecting a favorable version, or relabeling the archive as a prospective test.")

H("10. Conclusion", 1)
P("This study asked: **To what extent can a general-purpose AI autonomously develop a machine-learning system for short-term financial market prediction, and can the resulting system provide a promising foundation for further research?** In this project, the AI assistant made meaningful contributions to development and research-support work, as reported by the project author and reflected in the resulting technical artifacts. The evidence supports describing Demand Zone AI as a human-directed, AI-assisted system—not as a system autonomously conceived, validated, and delivered end to end. The user retained material control over the goal, constraints, and interpretation; complete process logs and contribution records are unavailable, so no autonomy percentage or generalization to other AI systems is justified.")
P("Demand Zone AI can be considered a promising but incomplete foundation for further research in an engineering and methodological sense. Its archived datasets and saved predictions, model inventory, development history, audit findings, and frozen v1.0.2 protocol give future work a concrete starting point. The 153 source CSV hashes, both primary table hashes, and all eight model hashes passed archive checks; OOF/event/label consistency passed; and pooled/fold point metrics plus AUC differences of +0.081757 and +0.005688 were recalculated from retained predictions. These checks do not reproduce the historical feature-generation, model-fitting, or prediction-generation pipeline.")
P("Important gaps remain: exact historical source is unavailable; feature parity failed; the seven archived bootstrap bounds remain unreproduced; V1–V7 results were not matched; the negative V2 simulation remains historical report evidence; and the NKE leakage episode lacks supporting detail. The v1.0.2 protocol is frozen but unexecuted, with no prospective prediction or outcome. Accordingly, the project does not establish predictive effectiveness, confirmed predictive value, profitability, causality, reliable calibration, or prospective performance. Its defensible contribution is a useful research starting point and a clearer account of the work still required—not a claim that either the AI development process or the resulting financial predictor has been independently proven effective.")

H("References", 1)
P("[1] Gu, S., Kelly, B., & Xiu, D. (2020). Empirical Asset Pricing via Machine Learning. *The Review of Financial Studies, 33*(5), 2223–2273. https://doi.org/10.1093/rfs/hhaa009")
P("[2] Sullivan, R., Timmermann, A., & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *The Journal of Finance, 54*(5), 1647–1691. https://doi.org/10.1111/0022-1082.00163")
P("[3] Harvey, C. R., Liu, Y., & Zhu, H. (2016). ...and the Cross-Section of Expected Returns. *The Review of Financial Studies, 29*(1), 5–68. https://doi.org/10.1093/rfs/hhv059")
P("[4] Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2017). The Probability of Backtest Overfitting. *The Journal of Computational Finance, 20*(4), 39–69. https://doi.org/10.21314/JCF.2016.322")
P("These references provide background on machine learning in asset pricing, data snooping, multiple testing, and backtest overfitting. They do not validate Demand Zone AI or any project result.")

PB()
H("Supplementary Materials", 1)
P("The following evidence matrix and tables are part of this standalone manuscript. They are intended to let a reviewer trace each major quantitative or methodological claim to a retained project source and understand exactly what was verified. Internal artifact paths are repository-relative. Historical reports are cited as reports, not treated as independent reproductions.")
H("Supplementary A. Claim-to-evidence matrix", 2)
C("Table S1. Evidence matrix. Classification applies to the stated claim, not to every assertion in its cited source.")
T(["ID", "Claim and evidence classification", "Exact source / artifact and audit boundary"], [
    ["E1", "153/153 source CSV hashes matched — Verified by audit.", "I1 (audit closeout), I3 (run_manifest.json), I7 (read-only audit utility). This is digest identity against the v1.0.1 manifest, not point-in-time data validation."],
    ["E2", "Both primary result-table hashes matched — Verified by audit.", "I1 and I3; exact SHA-256 values reproduced in Supplementary B. Identity of retained event/OOF tables only."],
    ["E3", "All eight saved model hashes matched — Verified by audit.", "I1, I3, I6. Hash match verifies preserved model files against manifest, not original code, training procedure, or feature semantics."],
    ["E4", "61,045 event/label rows; 41,221 unique finite OOF rows; 19,824 non-OOF rows — Verified by audit.", "I1–I5. Table counts and retained row identity; no model fit was performed."],
    ["E5", "OOF event IDs, labels, returns, entry/exit dates align; inclusive hold1 >= 2% labels and maturity checks pass — Verified by audit.", "I1, I4, I5. Applies to retained event and OOF tables; does not verify upstream OHLCV/feature-generation source."],
    ["E6", "Pooled/fold point metrics in Table 3 and Supplementary C tables — Recalculated from retained predictions.", "I1–I5. Recomputed from saved OOF score columns and labels; pooled values match I2/I3 to their reported precision. No refitting or feature replay."],
    ["E7", "LightGBM A − Logistic A = +0.0817570837 AUC — Recalculated from retained predictions.", "I1–I5; saved-score contrast and archived interval are in Table 4. The interval is not recalculated."],
    ["E8", "LightGBM C − LightGBM B = +0.0056875596 AUC — Recalculated from retained predictions.", "I1–I5. A score-column contrast only; failed feature parity prevents confident attribution to intended zone inputs."],
    ["E9", "Two primary and five secondary bootstrap interval bounds appear in the archive — Historical reported result; not reproduced.", "I2 and I3. Prior reconstructed-helper calculation failed to reproduce all seven; cause unknown. Closeout did not rerun bootstrap. Do not call verified intervals."],
    ["E10", "V1–V7 values in Table 1, including V1 .619 and V2 CatBoost .675950 — Historical reported result.", "I8–I13 and associated trainer code I16. Reports/metadata only; no matched reruns. Targets/folds/features vary by version."],
    ["E11", "V2 negative simulation (1,228 trades, 47.6%, −0.04% average, PF .97, Sharpe −.16, PnL −$9.77) — Historical reported result.", "I8 (V2 report) and I16 (builder/trainer source). The archive audit did not execute/reproduce this simulation; implementation needs review."],
    ["E12", "Legacy forward benchmark-return predictor path, including bench_XLK_hold1 — Source-level methodological risk; effect not quantified.", "I16 (build_v2_dataset.py, train_v2.py) and I8 (top-feature list). Code/report document risk; no leakage-corrected matched rerun."],
    ["E13", "V4/V5 target encodings, validation reuse and V7 variance-selection concerns — Source-level methodological risks; score impact unavailable.", "I10–I13 plus backend/train_v4.py, backend/train_v5.py, backend/train_v7.py. V4 month encoding uses within-month outcomes after some rows; V5 month/sector aggregates use broad target outcomes. V7 OOF selection uses fold-1 training variance, while the final saved fit uses full-dataset variance. Risk assessment, not a numeric leakage estimate."],
    ["E14", "V10–V13 target and feature lineage; proxy labels — Verified in inspected source code / historical dataset design, not performance evidence.", "I14 and I15. Scripts show label derivation; no controlled, independently verified V10–V13 performance sequence."],
    ["E15", "NKE leakage episode — Not verified / unavailable beyond project-author recollection.", "No event-level feature/date/mechanism or matched before/after artifact was found in the retained audit materials. Supporting incident detail is missing; do not quantify effect."],
    ["E16", "Exact historical v1.0.1 source file and complete per-version run bundles — Not verified / unavailable.", "I1–I3 and I16. Manifest contains historical source digest 29885c…; no intact matching .py or complete matched V1–V7 bundles recovered."],
    ["E17", "AAL reconstruction comparison: all 480 aligned AAL rows differ for rsi14, atr_pct, and zone_width_pct — Reconstructed but not matched.", "I1 and I18 (development/audit records); scoped comparison only. Prefix event counts and ID order matched, not feature values."],
    ["E18", "Old bytecode replay — Not reproduction evidence.", "I1 and I18. Previously unreviewed bytecode hash c7d23… was overwritten; current cache hash ee9017…; no trusted matching copy."],
    ["E19", "V2–V7 reported target/metric variations — Historical reported result, not an apples-to-apples series.", "I8–I13. Different labels, feature counts, and procedures; historical report values do not identify incremental version effects."],
    ["E20", "Frozen v1.0.2 event/label/feature/model/fold/prospective rules — Protocol specification only; not executed.", "I17 (frozen JSON, version 1.0.2, decision date 2026-09-28). It is not an output or run manifest; no v1.0.2 result exists."],
    ["E21", "Zero prospective predictions and zero prospective outcomes — Verified status in the archive closeout record.", "I1 and I17. No prospective lock or ledger exists in the record; no historical rows may be backfilled as prospective evidence."],
    ["E22", "149-symbol universe and OHLCV point-in-time provenance — Partially documented; historical membership/vintages unavailable.", "I3, I8, I17, I18. File hashes and cached coverage are recorded, but constituent history and original vendor vintages are not verified."],
    ["E23", "Historical V2 calibration numbers — Historical report only; reliable calibration not established.", "I8 and I16. Calibration workflow is not reproduced and uses the collected OOF sample in a non-chronological calibration routine; no v1.0.2 calibration run."],
    ["E24", "Archive source-prefix event count/order match — Reconstructed but not matched.", "I1 and I18. Matching counts/IDs is weaker than feature parity or end-to-end metric reproduction."],
    ["E25", "The project author used a general-purpose AI assistant to develop the model and related project components — Author-reported process evidence; not independently verified from complete logs.", "I19. The user's retrospective disclosure in the project conversation; no complete contemporaneous prompt/tool transcript, file-level contribution ledger, controlled baseline, or quantified autonomy measure is available. Supports a case-specific human-directed AI-assistance account, not a general autonomous-AI capability claim."],
], [650, 3100, 5610])

H("Supplementary B. Archive and hash verification", 2)
C("Table S2. Immutable v1.0.1 archive verification summary.")
T(["Artifact / check", "Recorded or audited result", "Classification / what the check establishes"], [
    ["Source CSV files", "153 of 153 SHA-256 hashes match the run manifest.", "Verified by audit: file identity relative to manifest; not point-in-time price provenance."],
    ["event_table.csv", "SHA-256 232de7db65c92bec249be801e593acdaa822ecd0b13eb0cd32b7eeaced85a4d0", "Verified by audit: retained primary-table digest."],
    ["oof_predictions.csv", "SHA-256 011530761a19016f430232f631a9c3b0199ac17aff297e491d8d50d4b1508829", "Verified by audit: retained primary-table digest."],
    ["Saved model files", "8 of 8 model artifact SHA-256 hashes match manifest.", "Verified by audit: see Supplementary C for file inventory; hash match does not prove training provenance."],
    ["Historical code digest", "29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b", "Manifest-recorded v1.0.1 source hash; matching intact source file unavailable."],
    ["Historical protocol digest", "486f46f85c4874405716a7c9424dc7060b5f65b27426e92670f0585247dfec07", "Manifest-recorded v1.0.1 protocol hash; not the frozen v1.0.2 protocol."],
    ["Saved model digests", "All 8/8 names and SHA-256 values are enumerated in Supplementary C.", "Manifest-checked hashes; an explicit inventory without a refit or semantic validation."],
    ["OOF / event rows", "61,045 event/label rows; 41,221 unique finite OOF rows; 19,824 event rows not scored OOF.", "Verified by audit from retained tables."],
    ["Validation year counts", "2023: 13,924; 2024: 13,180; 2025: 14,117; cached OHLCV history through 2026-08-03.", "Verified/recalculated from retained OOF rows; signal-date range 2023-01-03 to 2025-12-31. Cached coverage is not a point-in-time data vintage."],
    ["Signal cutoff", "All retained scored signal dates before exclusive 2026-01-01 cutoff.", "Verified by audit against saved dates; does not convert historical dates into a prospective test."],
    ["Metrics", "Pooled and fold-level point metrics recalculated from retained scores and match manifest/report to stated precision.", "Recalculated from retained predictions; upstream event/feature/model generation not reproduced."],
], [1650, 3970, 3740])

H("Supplementary C. Model and score inventory", 2)
C("Table S3. Eight retained model artifacts and manifest SHA-256 digests; all matched in the archive audit.")
T(["Model artifact", "SHA-256 digest"], [
    ["LogisticRegression_A.joblib", "470c614d8ce17211f8b58a05a43d69ba72f91a5127053b52316e839fb901397a"],
    ["LogisticRegression_B.joblib", "fe49917b20ce769bc713d6b674d80e5c41c25590fa84b3f8c094a48e9fb3e966"],
    ["LogisticRegression_C.joblib", "cc2826ced69ded12ba04980d74306d8a9ec9a275eed2450ed7653639359b0da4"],
    ["LogisticRegression_D.joblib", "1fd66c37e9f62202e4c5dd9235b6e1803ef795130b515eff76d62a7a59b8508b"],
    ["LightGBM_A.joblib", "f1a47ee24db9905cd9ff9558b4bc08e9d3bf6bdeaa1f39184a1613cb41604716"],
    ["LightGBM_B.joblib", "fe78f97012d31138bdad8fa0113e31b55ece9a73394a44db6a4dfc3a436ed6cd"],
    ["LightGBM_C.joblib", "af5f6143a3f8c216dd5bca8c6cfb5e76343d4fe0ebe702da554b93230a5b40bb"],
    ["LightGBM_D.joblib", "831963117ce578b9f619996aac1c1ee03e71922b032f422f2dfe903ea3338d21"],
], [3000, 6360])
P("All files are under `outputs/study_v1/models/`. The audit verified their digests against the v1.0.1 manifest. The retained OOF file contains corresponding saved score columns; hash identity does not establish how models were fitted, and the inventory does not assert that the objects can be refit from the unavailable original source.")
C("Table S4. Complete archived pooled-score comparison. Point metrics were recalculated from retained OOF predictions; rounded to four decimals as in the report.")
T(["Model / arm", "OOF n", "Positive rate", "ROC-AUC", "Average precision", "Mean daily AUC", "Top-5 precision / base"], [
    ["Logistic A", "41,221", "16.48%", "0.5901", "0.2324", "0.5883", "28.35% / 16.12%"],
    ["Logistic B", "41,221", "16.48%", "0.6608", "0.2688", "0.6815", "32.57% / 16.12%"],
    ["Logistic C", "41,221", "16.48%", "0.6603", "0.2663", "0.6752", "32.52% / 16.12%"],
    ["Logistic D", "41,221", "16.48%", "0.6596", "0.2655", "0.6732", "31.68% / 16.12%"],
    ["LightGBM A", "41,221", "16.48%", "0.6718", "0.2610", "0.6692", "30.10% / 16.12%"],
    ["LightGBM B", "41,221", "16.48%", "0.6778", "0.2739", "0.6931", "30.70% / 16.12%"],
    ["LightGBM C", "41,221", "16.48%", "0.6835", "0.2768", "0.6940", "30.95% / 16.12%"],
    ["LightGBM D", "41,221", "16.48%", "0.6848", "0.2748", "0.6944", "30.90% / 16.12%"],
], [1450, 800, 1000, 1150, 1450, 1600, 1910])
P("The primary archive report lists mean daily AUC over 728 dates with both classes and a same-date base rate of 16.12%. Metrics describe event-ranking performance within the saved archive. They are not a return series, execution model, probability-calibration test, or broad-market rate.")
C("Table S5. Fold-level saved OOF AUCs; audit recalculation matched archived report/manifest to reported precision.")
T(["Validation year", "Validation events", "Logistic A", "Logistic B", "Logistic C", "Logistic D", "LightGBM A", "LightGBM B", "LightGBM C", "LightGBM D"], [
    ["2023", "13,924", "0.6093", "0.6655", "0.6755", "0.6707", "0.6696", "0.6881", "0.6907", "0.6920"],
    ["2024", "13,180", "0.5840", "0.6750", "0.6759", "0.6769", "0.6798", "0.6685", "0.6801", "0.6806"],
    ["2025", "14,117", "0.5742", "0.6803", "0.6708", "0.6726", "0.6670", "0.6876", "0.6898", "0.6904"],
], [1250, 1380, 840, 840, 840, 840, 840, 840, 840, 850])
P("Fold AUC is recalculated on each retained fold's scored rows. This is not a refit of the corresponding model. The archived report's fold training counts (19,765 for 2023; 33,680 for 2024; 46,827 for 2025) are historical report/manifest values and are not asserted here as reproduced training partitions.")
C("Table S6. Primary contrast values and interval status.")
T(["Contrast", "Point estimate", "Archived 95% bounds", "Status"], [
    ["LightGBM A − Logistic A", "+0.08175708370456725", "[0.06575088322937951, 0.09902681483004104]", "Point recalculated; bounds archive-reported only."],
    ["LightGBM C − LightGBM B", "+0.00568755963220402", "[0.002178515954944907, 0.009191280185707295]", "Point recalculated; bounds archive-reported only."],
], [2300, 2050, 3000, 2010])
P("The historical archive lists five additional paired interval bounds, for seven total. A previous full attempt using the current reconstructed helper did not reproduce any of the seven; no secondary bounds are upgraded to verified evidence. The archived procedure is described as a weekly block bootstrap in the historical report. The more specific 1,000-resample, four-calendar-week, seed-42 rule is in the frozen v1.0.2 protocol and must not be represented as an executed v1.0.1 or v1.0.2 calculation.")
C("Table S7. All seven archived interval bounds: primary contrasts are reproduced in Table S6; secondary values below are historical report values only.")
T(["Historical contrast", "Archive-reported Δ AUC", "Archive-reported interval", "Current audit status"], [
    ["LightGBM A − Logistic Regression A", "+0.0818", "[0.06575088322937951, 0.09902681483004104]", "Point recalculated; interval not reproduced."],
    ["LightGBM C − LightGBM B", "+0.0057", "[0.002178515954944907, 0.009191280185707295]", "Point recalculated; interval not reproduced."],
    ["Logistic Regression B − A", "+0.0707", "[0.0503, 0.0947]", "Reported only; no interval reproduced."],
    ["LightGBM B − A", "+0.0060", "[−0.0086, 0.0217]", "Reported only; no interval reproduced."],
    ["Logistic Regression C − B", "−0.0004", "[−0.0044, 0.0035]", "Reported only; no interval reproduced."],
    ["Logistic Regression D − C", "−0.0007", "[−0.0034, 0.0019]", "Reported only; no interval reproduced."],
    ["LightGBM D − C", "+0.0013", "[−0.0019, 0.0051]", "Reported only; no interval reproduced."],
], [2600, 1600, 3000, 2360])

H("Supplementary D. Reconstruction and feature-parity comparison", 2)
C("Table S8. Scoped AAL feature-parity comparison; reconstruction was not matched.")
T(["Ticker", "Feature", "Aligned rows", "Differing rows", "Classification"], [
    ["AAL", "rsi14", "480", "480", "Reconstructed but not matched."],
    ["AAL", "atr_pct", "480", "480", "Reconstructed but not matched."],
    ["AAL", "zone_width_pct", "480", "480", "Reconstructed but not matched."],
], [900, 2500, 1500, 1500, 2960])
P("All 480 aligned AAL rows differed for each of the three tested features. The event-count and ordered-ID match does not imply feature parity.")
C("Table S10. What aligned, what failed, and what was not attempted.")
T(["Comparison dimension", "Observed status", "Interpretation"], [
    ["Event counts", "Available source-prefix reconstruction matched archived event counts.", "Partial structural agreement only."],
    ["Ordered event identifiers", "Prefix comparison matched archived event-ID order.", "Does not imply matching feature values, labels from original code, or predictions."],
    ["Feature prefix", "Multiple feature values differed.", "Feature parity failed; no end-to-end source equivalence."],
    ["AAL scoped features", "All 480 aligned AAL rows differed for each of rsi14, atr_pct, and zone_width_pct.", "One-symbol scoped comparison, not a full market replay; strong counter-evidence to feature parity."],
    ["Model fitting / predictions", "No recovered-source fold refit or historical prediction regeneration.", "Saved-score calculations are not pipeline reproduction."],
    ["Bootstrap", "Prior reconstructed helper failed to reproduce all seven archived bounds; cause unknown.", "Intervals remain archive-reported; no replacement presented."],
    ["Old bytecode", "Earlier replay was explicitly unreviewed; cache was later overwritten; matching copy absent.", "Cannot serve as trusted historical-source evidence."],
], [1850, 4100, 3410])
P("The v1.0.1 manifest's exact Python code SHA-256 is 29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b. The formerly recorded bytecode hash is c7d23b68e66d76f1f851887bc755b84b6bb1c8c424c24cccc8bf94de59d8f585; the overwritten cache currently has hash ee9017b7cf354931d638cb83bdc276c341bad9e90278addcdeec9ba60b4a7ed6. The current cache is not the old artifact. No claim is based on either as a source restoration.")

H("Supplementary E. Versioned historical results and non-comparability", 2)
C("Table S11. Expanded V1–V7 report/metadata inventory.")
T(["Version", "Target(s) / procedure as reported", "Reported quantitative values", "Evidence category / caveat"], [
    ["V1", "XGBoost, hold1; 50 features (quoted by later V2 report).", "AUC 0.619; top-5 rate 29.0%.", "Historical quotation; exact V1 bundle unavailable."],
    ["V2", "44,854-row dataset; hold1 and additional alpha/barrier tasks; five chronological folds in report.", "CatBoost mean AUC 0.675950 (SD 0.022838); Random Forest reported top-5 precision 33.55%, CatBoost 31.93%. Negative simulation: 1,228 trades; win 47.6%; avg −0.04%; PF .97; Sharpe −.16; total PnL −$9.77.", "All report-level. No independently reproduced model or trading simulation; feature leakage and implementation concerns."],
    ["V3", "Five-fold metadata across hold1, alpha-SPY, and alpha-sector labels; 281 listed features.", "alpha_spy_2pct AUC .728106; hold1_2pct .671232; alpha_spy_1pct .710673.", "Historical metadata, not a rerun; includes risk from forward benchmark fields."],
    ["V4", "Three-model ensemble metadata; alpha_spy_2pct; 407 features; target encodings and recency weighting described by code.", "OOF .744640; test .727987; top-5 53.492%.", "Historical metadata; test/OOF labels do not establish independent confirmation; full-sample outcome encoding risk."],
    ["V5", "Three-model ensemble; selected alpha_spy_3pct; 428 features.", "OOF .784078; test .752945; top-5 43.132%; positive base rate 11.854%.", "Historical metadata; different target/base rate from V4; no matched comparison."],
    ["V6", "Magnitude plus same-day closing-move tasks.", "Magnitude AUC .725831; same-day absolute move AUC .760557.", "Historical metadata; not the next-open hold1 endpoint."],
    ["V7", "Three-fold equal-weight tree ensemble; 400 total candidate features, 120 retained per metadata. OOF feature set is chosen from fold-1 training variance; final saved-model feature set is chosen using the full dataset.", "OOF hold1_2pct .7084; alpha_spy_2pct .7049; magnitude .6989.", "Historical metadata; final-fit feature selection includes full-dataset variance, but this fact alone does not show OOF metric leakage; no matched rerun."],
], [620, 3300, 2940, 2500])
P("Additional V2 report details include a 2021-08-03 to 2026-06-24 dataset interval, reported expanding/rolling/leave-one-year-out analyses, calibration numbers, and an `bench_XLK_hold1` feature-importance entry. These are historical report values and not audited metrics. V4–V7 metadata were created during the same development period and cannot be treated as untouched, prospective tests.")
C("Table S12. Separate V10–V13 dataset augmentation inventory.")
T(["Stage", "New columns / label logic documented in code", "Evidence status"], [
    ["V10", "20-session demand-zone barrier simulation; target/stop, hit_target, MFE/MAE and return fields.", "Inspected generator source; no full matched dataset/run inventory."],
    ["V11", "Derived interaction/zone features; market_relative_hit copies hit_target.", "Source code confirms proxy construction; not a measured market-relative outcome."],
    ["V12", "strong_hit = hit_target AND SPY 20-day return > −0.01; additional market/zone features.", "Source code confirms a transformed target; not an independently observed alpha outcome."],
    ["V13", "Heuristic hit_5pct/hit_10pct/hit_20pct and target tier; expected-return and risk-adjusted proxies; regime/structure features.", "Source code confirms heuristics; these proxy labels are not actual realized barrier hits."],
], [850, 5790, 2720])

H("Supplementary F. Methodological risk and unavailable-evidence register", 2)
C("Table S13. Risk, evidence, and conclusion allowed.")
T(["Issue", "What the retained evidence supports", "What remains unknown / permitted conclusion"], [
    ["Forward benchmark predictors", "V2 builder creates benchmark hold1 returns; trainer exclusion list is not a full benchmark-family block; report lists bench_XLK_hold1 among top features.", "Leakage path is documented in inspected code/report. Its effect on AUC is unmeasured; no corrected score estimate."],
    ["Full-sample outcome encodings", "V4 code computes month hit rates using all rows in a month; V4/V5 code and documentation include outcome-derived encodings.", "Methodological leakage/validation concern; no exact effect or per-version corrected rerun."],
    ["Feature-selection/validation reuse", "V2 screens features using target-dependent statistics before folds; V4 ensemble design describes fold-AUC weighting; V7 reuses first-fold training variance for OOF feature pruning and recomputes full-dataset variance for the final saved model.", "Risk to interpretation; the final-fit variance choice alone does not demonstrate OOF leakage. Not proof every reported value is invalid and not a numeric leakage attribution."],
    ["Label validity", "Legacy builder creates threshold labels before final missing-target drop; frozen protocol requires finite positive forward opens before binarization.", "Potential failure if downstream filtering is bypassed; audited retained v1.0.1 labels do align with saved returns and threshold."],
    ["Barrier ordering", "Inspected generator checks target before stop on daily OHLC bars.", "Same-day double-touch outcome is convention-dependent; no claim about exact historic impact."],
    ["NKE incident", "Project-author recollection of a leakage episode.", "No exact feature/date/mechanism or before/after artifact; not independently verified or quantifiable."],
    ["V2 trading simulation", "V2 report records negative results; current trainer code contains position and timing logic requiring review.", "Historical report only; no independently confirmed transaction-level or net strategy estimate."],
    ["Bootstrap bounds", "Seven bounds are retained in historical report/manifest; reconstructed helper failed all seven previously.", "Root cause unknown; intervals are not verified. No replacements."],
    ["Data and universe", "Manifest fixes hashes for 153 cached CSVs and a recovered 149-symbol roster.", "Point-in-time data vintages, historical constituents, delisted names and roster-selection date are unavailable."],
    ["Prospective status", "Protocol is frozen as v1.0.2 in JSON.", "No lock/ledger/prediction/outcome; no prospective conclusion or v1.0.2 metric exists."],
], [1800, 4000, 3560])
H("Unavailable materials that materially limit reproducibility", 3)
for item in [
    "An intact historical Python source file matching v1.0.1 code SHA-256 29885c5f14235e78349b728156e18feba930f3ee533565ea36a05f695692424b.",
    "Complete, mutually matched V1–V7 run bundles: source revision, exact inputs and hashes, feature matrix, row IDs, preprocessing, fold assignments, training logs, OOF predictions, model files, dependency environment, and report for each version.",
    "Point-in-time daily OHLCV vintages, historical universe membership, delisted-issuer coverage, and original date/criterion for choosing the 149-symbol roster.",
    "The exact historical bootstrap implementation/inputs or a known cause for its mismatch with the seven retained interval bounds.",
    "Supporting NKE incident documentation: affected feature(s), event dates, mechanism, discovery record, and matched before/after runs.",
    "A matched, independently reproducible V2 trade ledger and verified transaction-cost/position accounting for the reported negative simulation.",
    "Any prospective v1.0.2 lock, append-only prediction/outcome ledger, fresh post-lock scores, and matured outcomes; none are present.",
]:
    B(item)

H("Supplementary G. Frozen v1.0.2 design reference (not an execution report)", 2)
C("Table S14. Key v1.0.2 protocol settings and their status.")
T(["Protocol component", "Frozen design", "Status in this paper"], [
    ["Version / date", "DZAI-MARKET-STRUCTURE-ABLATION-V1 v1.0.2; decision lock 2026-09-28; exclusive signal cutoff 2026-01-01.", "Protocol frozen; not an executed run."],
    ["Population", "One candidate retest event per ticker-session on fixed recovered 149-symbol roster.", "Roster rule specified; membership/survivorship limitations persist."],
    ["Event timing", "After close T; swing low confirmed at i+2; retest tolerance 3%; maximum five retest starts per zone; one event per ticker-date.", "Specification only; historical source equivalence not established."],
    ["Primary label", "Open[T+2]/Open[T+1]−1; positive if >=2%; finite positive opens and return required before binarization.", "Specification only; no v1.0.2 labels/scores produced."],
    ["Feature arms", "A/B/C/D = 20/38/65/99 nested features (baseline/context/demand-zone/order-block).", "Whitelist frozen; reconstruction did not match archived features."],
    ["Estimators", "Fixed Logistic Regression and LightGBM with fold-local transforms; no tuning, ensembles, calibration or result selection.", "Settings specified; no v1.0.2 model fitting claimed."],
    ["Historical folds", "Annual validation for 2023, 2024, 2025; training label exit strictly before validation start.", "Design only; v1.0.1 saved scores are not proof of conformance."],
    ["Uncertainty", "Planned 1,000 circular four-calendar-week block resamples, seed 42, for descriptive paired intervals.", "No v1.0.2 interval exists; v1.0.1 archived bounds remain unreproduced."],
    ["Prospective ledger", "Append-only hash-chained predictions before outcomes; no backfill/retraining; source/model/code/protocol provenance recorded.", "No lock or ledger exists; zero prospective predictions/outcomes."],
    ["Prospective stopping", "Stop at 2,000 events or 18 months; final analysis only after >=12 months and >=2,000 matured outcomes.", "Future criteria only; no performance inference."],
], [1750, 4790, 2820])
P("The frozen design improves auditability by fixing event timing, target validity, nested feature names, model settings, chronological label-maturity purging, and append-only prospective logging before data collection. It cannot cure the retrospective feature mismatch or validate legacy reports. If executed in the future, it will answer a conditional ranking question for a fixed candidate-event population; it will not by itself establish causal support, representativeness of all equities, or a profitable strategy.")

H("Supplementary H. Evidence vocabulary and interpretation rules", 2)
C("Table S15. Terms used consistently throughout the manuscript.")
T(["Term", "Operational meaning in this paper", "Example"], [
    ["Verified by audit", "A retained artifact property directly checked by the bounded read-only archive audit.", "153/153 CSV digests match the manifest; OOF/event IDs align."],
    ["Recalculated", "A statistic recomputed from saved prediction scores/labels without rebuilding or fitting the pipeline.", "Pooled and fold AUC; paired AUC point differences."],
    ["Historical / reported", "A number or method stated in a retained report, metadata file, or project source but not matched by this audit.", "V2 backtest; V3–V7 AUC values; archived intervals."],
    ["Reconstructed but not matched", "Behavior in current editable code or bounded comparison that is not feature/source-equivalent to archive.", "Event counts/ID order match, but AAL feature values differ."],
    ["Not verified / unavailable", "Evidence needed to confirm the claim is not present or was not executed.", "NKE mechanism; original source; prospective results."],
    ["Frozen protocol", "A prespecified design whose requirements are recorded before a future evaluation.", "v1.0.2 JSON. A protocol is not an experiment or result."],
], [1730, 4220, 3410])
P("The following inference rules apply: (1) hash identity is not semantic validity; (2) arithmetic on retained scores is not upstream pipeline reproduction; (3) historical OOF or test labels do not become prospective by later documentation; (4) different targets or selected model versions are not a controlled comparative sequence; (5) AUC and top-k precision are not trading returns; (6) an unverified interval must not be reported as independently reproduced; and (7) a reported leakage episode without traceable details is not an established causal explanation.")

H("Supplementary I. Internal project artifact key", 2)
P("The following repository-relative artifact paths provide source traceability for matrix IDs E1–E25. The path registry identifies where evidence resides; the claim's evidence classification is stated in Table S1.")
C("Table S16. Project evidence sources.")
T(["ID", "Repository-relative path(s)", "Primary use in this manuscript"], [
    ["I1", "outputs/study_v1_archive_audit_closeout.md", "Bounded audit scope, hash passes, counts, alignment checks, saved-score metric status, feature-parity and bootstrap caveats, prospective status."],
    ["I2", "outputs/study_v1/development/development_report.md", "Archived pooled/fold metrics, target, counts and historical limitations; report is not a matched rerun."],
    ["I3", "outputs/study_v1/development/run_manifest.json", "Historical code/protocol hashes, source data hashes, table hashes, model metadata, roster and run settings."],
    ["I4", "outputs/study_v1/development/event_table.csv", "Retained event/label rows; identity checked against OOF rows by audit."],
    ["I5", "outputs/study_v1/development/oof_predictions.csv", "Retained OOF labels and score columns used for recalculated point metrics."],
    ["I6", "outputs/study_v1/models/LogisticRegression_{A,B,C,D}.joblib; outputs/study_v1/models/LightGBM_{A,B,C,D}.joblib", "Eight retained model artifacts; audit verifies hashes only."],
    ["I7", ".freebuff/recovery_tools/audit_saved_v1_0_1_outputs.py", "Read-only saved-output audit utility; no feature regeneration or model fitting in its default audit."],
    ["I8", "outputs/v2/v2_report.md", "V2 dataset description, model benchmarks, negative simulation, calibration report, feature importance, V1 quotation."],
    ["I9", "models/v3/v3_metadata.json", "V3 target and AUC metadata."],
    ["I10", "models/v4/v4_metadata.json; backend/train_v4.py", "V4 reported metrics and source-level target-encoding/ensemble concerns."],
    ["I11", "models/v5/v5_metadata.json; backend/train_v5.py", "V5 reported metrics, target choice, feature/encoding workflow."],
    ["I12", "models/v6/v6_metadata.json", "V6 magnitude and same-day target metrics."],
    ["I13", "models/v7/v7_metadata.json; backend/train_v7.py", "V7 metadata, ensemble, feature pruning, and reported targets."],
    ["I14", "README.md; Python/generate_ml_dataset.py", "Early project objective, barrier simulation and evolving configuration."],
    ["I15", "Python/augment_v10_to_v11.py; Python/augment_v11_to_v12.py; Python/augment_v12_to_v13.py", "Separate V10–V13 feature and proxy-target lineage."],
    ["I16", "backend/build_hold1_targets.py; backend/build_v2_dataset.py; backend/train_v2.py", "Hold1 target construction, forward benchmark fields, V2 feature screening, calibration/backtest implementation."],
    ["I17", "MARKET_STRUCTURE_STUDY_V1_PROTOCOL.json", "Frozen v1.0.2 protocol specification; not an execution record."],
    ["I18", "Demand_Zone_AI_Development_and_Audit_Record.docx; Market_Structure_Experiment_Protocol.docx", "Companion project-development and protocol/audit records; not substitutes for raw run bundles."],
    ["I19", "Project-author retrospective disclosure during manuscript preparation; no complete archived development interaction log.", "AI-use attribution and limits of the autonomy assessment; not a source for model-performance claims."],
], [620, 3900, 4840])
P("Public-release availability note. The bounded closeout was previously run in the project workspace against the retained v1.0.1 files. In this public GitHub release, raw market-data CSVs, row-level event and OOF prediction tables, and serialized model binaries are intentionally omitted pending confirmed redistribution rights. Accordingly, source-key paths I4–I6 identify local artifacts used in the prior audit; they are not downloadable files in this public release. The manifest retains hash references, but hashes do not substitute for the omitted files. The reported integrity and saved-score checks describe that completed local audit and cannot be independently repeated from this public source-only bundle without separately obtained, appropriately licensed inputs and artifacts. Source code and methodology are included to support review; data and binaries must be obtained independently under applicable permissions. This manuscript does not modify the immutable v1.0.1 archive or frozen v1.0.2 JSON.")

# Assemble document XML.
doc = ET.Element(q(W, "document"))
body = add(doc, W, "body")
for block in blocks:
    kind = block[0]
    if kind == "title":
        node = p(block[1], "Title", align="center", keep=True, after=220)
    elif kind == "subtitle":
        node = p(block[1], "Subtitle", align="center", keep=True, after=240)
    elif kind == "covernote":
        node = p(block[1], "CoverNote", align="center", after=160)
    elif kind == "h":
        heading(block[1], block[2])
    elif kind == "p":
        p(block[1], "Normal")
    elif kind == "b":
        bullet(block[1])
    elif kind == "n":
        number_item(block[1], block[2])
    elif kind == "f":
        formula(block[1])
    elif kind == "c":
        caption(block[1])
    elif kind == "t":
        table(block[1], block[2], block[3])
    elif kind == "pb":
        page_break()

sect = add(body, W, "sectPr")
add(sect, W, "headerReference", {q(W, "type"): "default", q(R, "id"): "rIdHeader"})
add(sect, W, "footerReference", {q(W, "type"): "default", q(R, "id"): "rIdFooter"})
add(sect, W, "pgSz", {q(W, "w"): "12240", q(W, "h"): "15840"})
add(sect, W, "pgMar", {q(W, "top"): "1440", q(W, "right"): "1440", q(W, "bottom"): "1440", q(W, "left"): "1440", q(W, "header"): "720", q(W, "footer"): "720", q(W, "gutter"): "0"})
add(sect, W, "cols", {q(W, "space"): "720"})
add(sect, W, "docGrid", {q(W, "linePitch"): "360"})

styles = ET.Element(q(W, "styles"))
def style(style_id, name, based=None, font="Times New Roman", size="21", bold=False, color="222222", italic=False, before="0", after="120", line="276", align=None, keep=False):
    s = add(styles, W, "style", {q(W, "type"): "paragraph", q(W, "styleId"): style_id})
    add(s, W, "name", {q(W, "val"): name})
    if based:
        add(s, W, "basedOn", {q(W, "val"): based})
    ppr = add(s, W, "pPr")
    add(ppr, W, "spacing", {q(W, "before"): before, q(W, "after"): after, q(W, "line"): line, q(W, "lineRule"): "auto"})
    if align:
        add(ppr, W, "jc", {q(W, "val"): align})
    if keep:
        add(ppr, W, "keepNext")
    rpr = add(s, W, "rPr")
    add(rpr, W, "rFonts", {q(W, "ascii"): font, q(W, "hAnsi"): font, q(W, "cs"): font})
    add(rpr, W, "sz", {q(W, "val"): size})
    add(rpr, W, "color", {q(W, "val"): color})
    if bold:
        add(rpr, W, "b")
    if italic:
        add(rpr, W, "i")
    return s

style("Normal", "Normal", font="Times New Roman", size="21", color="222222", after="120", line="276", align="both")
style("Title", "Title", font="Aptos Display", size="38", bold=True, color="17365D", before="1800", after="260", line="300", align="center", keep=True)
style("Subtitle", "Subtitle", font="Aptos", size="24", color="365F91", after="280", line="300", align="center", keep=True)
style("CoverNote", "Cover Note", font="Aptos", size="20", color="555555", after="180", line="280", align="center")
style("Heading1", "Heading 1", font="Aptos Display", size="31", bold=True, color="17365D", before="360", after="150", line="300", keep=True)
style("Heading2", "Heading 2", font="Aptos Display", size="25", bold=True, color="2F5597", before="240", after="100", line="280", keep=True)
style("Heading3", "Heading 3", font="Aptos", size="22", bold=True, color="365F91", before="180", after="80", line="260", keep=True)
style("Caption", "Caption", font="Aptos", size="18", color="404040", bold=True, before="100", after="70", line="240", keep=True)
style("TableText", "Table Text", font="Arial", size="16", color="222222", after="0", line="210")
style("ListParagraph", "List Paragraph", font="Times New Roman", size="21", color="222222", before="0", after="70", line="276")

# Document defaults and compatibility settings.
docdefaults = add(styles, W, "docDefaults")
rprdefault = add(docdefaults, W, "rPrDefault")
rpr = add(rprdefault, W, "rPr")
add(rpr, W, "rFonts", {q(W, "ascii"): "Times New Roman", q(W, "hAnsi"): "Times New Roman", q(W, "cs"): "Times New Roman"})
add(rpr, W, "sz", {q(W, "val"): "21"})
add(rpr, W, "lang", {q(W, "val"): "en-US"})
styles.insert(0, docdefaults)

settings = ET.Element(q(W, "settings"))
add(settings, W, "zoom", {q(W, "percent"): "100"})
add(settings, W, "defaultTabStop", {q(W, "val"): "720"})
compat = add(settings, W, "compat")
add(compat, W, "compatSetting", {q(W, "name"): "compatibilityMode", q(W, "uri"): "http://schemas.microsoft.com/office/word", q(W, "val"): "15"})
add(settings, W, "doNotTrackMoves")
add(settings, W, "doNotTrackFormatting")

header = ET.Element(q(W, "hdr"))
hp = add(header, W, "p")
hppr = add(hp, W, "pPr")
add(hppr, W, "jc", {q(W, "val"): "right"})
hr = add(hp, W, "r")
hrpr = add(hr, W, "rPr")
add(hrpr, W, "rFonts", {q(W, "ascii"): "Aptos", q(W, "hAnsi"): "Aptos"})
add(hrpr, W, "sz", {q(W, "val"): "16"})
add(hrpr, W, "color", {q(W, "val"): "73869A"})
add(hr, W, "t", text="DEMAND ZONE AI  |  RETROSPECTIVE AUDIT")

footer = ET.Element(q(W, "ftr"))
fp = add(footer, W, "p")
fpr = add(fp, W, "pPr")
add(fpr, W, "jc", {q(W, "val"): "center"})
fr = add(fp, W, "r")
frpr = add(fr, W, "rPr")
add(frpr, W, "rFonts", {q(W, "ascii"): "Aptos", q(W, "hAnsi"): "Aptos"})
add(frpr, W, "sz", {q(W, "val"): "16"})
add(frpr, W, "color", {q(W, "val"): "73869A"})
add(fr, W, "t", text="Page ")
fld = add(fp, W, "fldSimple", {q(W, "instr"): "PAGE"})
fieldrun = add(fld, W, "r")
add(fieldrun, W, "t", text="1")

# Package-level relationships and properties.
rels = ET.Element(q(REL, "Relationships"))
for rid, typ, target in [
    ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "word/document.xml"),
    ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
    ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
]:
    add(rels, REL, "Relationship", {"Id": rid, "Type": typ, "Target": target})

docrels = ET.Element(q(REL, "Relationships"))
for rid, typ, target in [
    ("rIdStyles", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml"),
    ("rIdSettings", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings", "settings.xml"),
    ("rIdHeader", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header", "header1.xml"),
    ("rIdFooter", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer", "footer1.xml"),
]:
    add(docrels, REL, "Relationship", {"Id": rid, "Type": typ, "Target": target})

types = ET.Element(q(CT, "Types"))
add(types, CT, "Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
add(types, CT, "Default", {"Extension": "xml", "ContentType": "application/xml"})
for part, content_type in [
    ("/word/document.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"),
    ("/word/styles.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"),
    ("/word/settings.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"),
    ("/word/header1.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"),
    ("/word/footer1.xml", "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"),
    ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
    ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml"),
]:
    add(types, CT, "Override", {"PartName": part, "ContentType": content_type})

core = ET.Element(q("http://schemas.openxmlformats.org/package/2006/metadata/core-properties", "coreProperties"))
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
add(core, DC, "title", text="Can a General-Purpose AI Develop a Financial-Prediction System? A Retrospective Case Study of Demand Zone AI")
add(core, DC, "subject", text="Retrospective study of AI-assisted development and financial machine-learning reproducibility")
add(core, DC, "creator", text="Prepared from retained project artifacts; author details unavailable")
add(core, DC, "description", text="Standalone evidence-mapped manuscript; retrospective only, not investment advice.")
add(core, DCT, "created", {q(XSI, "type"): "dcterms:W3CDTF"}, "2026-09-30T00:00:00Z")
add(core, DCT, "modified", {q(XSI, "type"): "dcterms:W3CDTF"}, "2026-09-30T00:00:00Z")

app = ET.Element(q(EP, "Properties"))
add(app, EP, "Application", text="Freebuff DOCX generator (Python standard library)")
add(app, EP, "DocSecurity", text="0")
add(app, EP, "ScaleCrop", text="false")
heading_pairs = add(app, EP, "HeadingPairs")
vec = add(heading_pairs, VT, "vector", {"size": "2", "baseType": "variant"})
variant = add(vec, VT, "variant")
add(variant, VT, "lpstr", text="Title")
variant = add(vec, VT, "variant")
add(variant, VT, "i4", text="1")
titles = add(app, EP, "TitlesOfParts")
add(titles, VT, "vector", {"size": "1", "baseType": "lpstr"})

parts = {
    "[Content_Types].xml": types,
    "_rels/.rels": rels,
    "word/document.xml": doc,
    "word/_rels/document.xml.rels": docrels,
    "word/styles.xml": styles,
    "word/settings.xml": settings,
    "word/header1.xml": header,
    "word/footer1.xml": footer,
    "docProps/core.xml": core,
    "docProps/app.xml": app,
}

with ZipFile(OUT, "w", ZIP_DEFLATED) as zf:
    for name, root in parts.items():
        zf.writestr(name, ET.tostring(root, encoding="utf-8", xml_declaration=True))

# Validate package integrity, XML parts, article structure, and required evidence assertions.
with ZipFile(OUT, "r") as zf:
    assert zf.testzip() is None, "DOCX ZIP CRC failure"
    for name in zf.namelist():
        if name.endswith(".xml") or name.endswith(".rels"):
            ET.fromstring(zf.read(name))
    document_root = ET.fromstring(zf.read("word/document.xml"))
    doc_text = " ".join((node.text or "") for node in document_root.iter(q(W, "t")))
    table_nodes = list(document_root.iter(q(W, "tbl")))
    required = [
        "Can a General-Purpose AI Develop a Financial-Prediction System? A Retrospective Case Study of Demand Zone AI", "30 September 2026", "Abstract", "1. Introduction", "1.2 Research question", "general-purpose AI autonomously develop a machine-learning system",
        "1.4 Operational definitions and assessment approach", "3.5 Human–AI development process and autonomy assessment", "2. Background and project development", "3. Data and experimental development",
        "4. Reproducibility and audit method", "5. Results", "5.5 D. What the case shows about AI autonomy and research potential", "6. Methodological findings",
        "7. Frozen v1.0.2 protocol for a future experiment", "8. Discussion", "9. Limitations", "10. Conclusion",
        "References", "Supplementary A. Claim-to-evidence matrix", "Supplementary C. Model and score inventory", "153/153", "480 aligned AAL rows", "In this public GitHub release, raw market-data CSVs, row-level event and OOF prediction tables, and serialized model binaries are intentionally omitted",
        "+0.08175708370456725", "+0.00568755963220402", "zero prospective predictions and zero prospective outcomes",
        "all 480 aligned AAL rows differed", "failed to reproduce any of those seven bounds", "E25", "AI-assisted", "promising but incomplete foundation for further research", "not as a system autonomously conceived, validated, and delivered end to end",
    ]
    for phrase in required:
        assert phrase.casefold() in doc_text.casefold(), "Missing required manuscript phrase: " + phrase
    assert len(table_nodes) >= 12, "Expected manuscript and supplement evidence tables"
    assert len(doc_text) > 45000, "Manuscript content unexpectedly short"

sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
print("DOCX generated and validated:", OUT.relative_to(ROOT))
print("Bytes:", OUT.stat().st_size, "| Tables:", table_count, "| Paragraphs:", paragraph_count)
print("Document SHA-256:", sha)
print("Validation: ZIP CRC and all XML parts passed; required sections/evidence assertions passed.")
