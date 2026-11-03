# Milestone 11 Agents

| role | inputs | outputs | cannot do |
|---|---|---|---|
| lead | questions, hypotheses, budget | assignments + deferred + rationale | conclude anything |
| data_scientist | artifact facts | schema/hygiene brief + limits | run tools |
| model_analyst | executed actions | error brief (establishes / does-not) + limits | claim causes |
| experiment_designer | question, hyps, facts, ran, budget | top discriminating spec + alternatives | exceed budget |
| skeptic | hypotheses + evidence | blocking/advisory challenges + falsifiers | pass without evidence |
| judge | hypotheses + evidence refs ONLY | upheld / overturned / would-support / would-reject / undecided | see lead output |

Role boundaries tested: skeptic catches planted unsupported-support;
judge downgrades evidence-free supports and its signature is
source-inspected to exclude lead outputs.
