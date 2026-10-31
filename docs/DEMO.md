# Three-minute demonstration outline

## Preparation

Start the dashboard using the README before presenting. Use default mock mode
with `USE_PAPER_TRADING` and every `USE_REAL_*` option false. Keep the terminal
available and the browser on **Analysis & approval**. Use `AAPL` throughout.
No account, API keys or external service is needed after dependency installation.

Rehearse with a stopwatch. These allocations total 180 seconds, but actual speech
and clicks must be timed. Cut wording if needed and stop at three minutes. Keep
the representative screenshot available if the display cannot be shared.

## Timed outline

| Time | Action | Speaking points |
| --- | --- | --- |
| 0:00-0:20 | Show the idle analysis view. | "FinGraph helps students and beginners understand a decision process. Three specialist views come together, Python rules check the result, and a person makes the final decision. This mock demonstration cannot submit orders." |
| 0:20-0:50 | Run `AAPL`; open one analyst's evidence and risks. | "The agents return structured reports and can disagree. Signals, confidence, evidence and risks remain visible instead of disappearing behind one recommendation." |
| 0:50-1:20 | Open Risk details and briefly Run activity; return. | "The first mock proposal is too large. The independent risk engine rejects it and the decision model revises it. The log exposes that retry. Passing risk pauses this run for human approval." |
| 1:20-1:45 | Reject, then show Current execution. | "Reject resumes the paused run with a negative decision. The workflow ends and submits no order. Navigation preserves the run; it does not repeat the analysis." |
| 1:45-2:10 | Reset, run again and Approve. | "Approval resumes the existing thread. Execution is disabled in this submission, so it is skipped. The final refresh leads to END, not an automatic trading loop." |
| 2:10-2:25 | Reset, clear the ticker and Run analysis. | "Blank input produces a readable validation error before a graph starts. Entering a valid ticker lets the interface recover." |
| 2:25-2:50 | Point to the code map or keep the app visible. | "DashboardRunner is a class that owns a resumable run. A recursive serializer walks nested state for the redacted debug view. Tests cover decisions, risk, approval, nested state and dashboard interaction." |
| 2:50-3:00 | Finish on the app or representative image. | "The aim is an inspectable decision path: coordination, constraints and human oversight, rather than profit prediction." |

## Evidence for questions

- `app/dashboard_runner.py::DashboardRunner.start` and `resume_approval`:
  an object retains its graph and thread across the human decision.
- `app/dashboard_view.py::_serialize`: models, dictionaries, lists and tuples
  recurse; ordinary values form the stopping case.
- `nodes/risk_engine.py::risk_engine_node`: independent Python rules check
  proposals instead of relying on a model to pronounce itself safe.
- `tests/test_dashboard_view.py`, `tests/test_human_interrupt.py` and
  `tests/test_streamlit_app.py`: concrete checks supporting those claims.

Distinguish retained optional integrations from the default mock demonstration.
Do not describe mock reports as live research, an accepted paper order as a fill,
or a test fixture as a real trade.

