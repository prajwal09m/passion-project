# M14 Flagship (Phase 13)

demo/flagship_m14.py on unfamiliar c_robustness (machine scale
fault) executes all 17 stages with real artifacts: recon,
mechanism candidate (m2 ratio 614.19), validated composed
experiment, hash-guarded perturbation with map, adaptive single
(0.688) vs team (0.773) runs, skeptic/judge review, falsification
plan, independent verification (not-reproduced via independent
tool, reported as uncertainty), layered confidence, 4 risks,
memory transfer proposals, portfolio assessment, idempotent
resume, eval3 aggregate (0.709), and steady/thin controls. Test
test_flagship_m14_end_to_end asserts each stage. Run: py -c
"from model_autopsy.demo.flagship_m14 import run_flagship; ...".
