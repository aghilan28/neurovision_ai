NeuroVision — Phase 4 Clinical Report Integration Fix
=====================================================

Files in this bundle (place at repo root, overwriting the existing files):

  serve_local.py   — patched FastAPI backend (constants reordering, bipolar
                     channel matcher, deterministic IDs, real timestamps,
                     data-driven narrative, metadata block, honest
                     empty-states, telemetry preserved across predict)
  analysis.html    — patched Clinical Report page (recording metadata strip
                     bound to backend metadata.*; honest "No comparable
                     historical cases available" empty state)

Not modified: CSS, layout, other HTML pages, ML models, training scripts,
APIs, routing, or any other file.

To apply:
  1. Back up (or git commit) your existing serve_local.py and analysis.html
  2. Copy the two files over the originals at the repository root
  3. Restart the server:  python3 serve_local.py
  4. Verify: upload chb_test/chb01/chb01_01.edf and click
     "View Intelligence Report" — every value on the report page will now
     originate from the real EDF analysis.

See PHASE4_INTEGRATION_REPORT.md for the full root-cause analysis, line-
level before/after snippets, the UI→Backend mapping table, and verification
evidence.
