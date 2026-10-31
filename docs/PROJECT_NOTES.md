# Project notes and code explanation

## Problem and design choices

FinGraph explores how a decision can remain understandable when it combines
several information sources. Fundamental, technical and news reports keep their
own evidence and uncertainty. A Decision Agent combines them, deterministic Python
rules check the proposal, and a human can reject an eligible action.

The distinctive feature is the separation of responsibilities. Analysts cannot
authorize execution, model confidence does not replace risk checks, and dashboard
navigation does not start a new run. Default mock mode demonstrates an oversized
proposal, feedback, revision and human review without external services.

The workflow is a finite run with bounded decision retries. After an approved
action reaches execution, it refreshes the portfolio and ends. Default execution
skips submitting an order. There is no autonomous, continuously trading loop.

## Programming concepts with concrete uses

| Concept | Where to explain it | Why it is useful |
| --- | --- | --- |
| Classes and encapsulation | `app/dashboard_runner.py::DashboardRunner`, especially `start`, `resume_approval` and `_result_to_run` | One object owns the graph, thread identifier and interrupted state. The UI resumes the right run without duplicating backend logic. |
| Structured objects | `app/dashboard_runner.py::DashboardRun` and `schemas/` | A dataclass groups a result; validated models define consistent report, proposal, risk, execution and portfolio fields. |
| Recursion | `app/dashboard_view.py::_serialize`, called by `serializable_state` | The same function walks each nested model, dictionary, list or tuple. Ordinary values are the base case, avoiding a hard-coded nesting depth. |
| Error handling and validation | `DashboardRunner.start`, `DashboardRunner.resume_approval`, UI handlers and provider exceptions | Invalid tickers and resume states are rejected explicitly instead of being treated as successful runs. |
| Testing | `tests/`, pytest and Streamlit AppTest | Tests exercise logic, integration boundaries and user interaction without real services. |

Classes and recursion are distinct concepts demonstrated by this code. Whether
they satisfy the advanced-concepts component depends on the course's official
topic list. Explain the implementation and its purpose; installing a library alone
is not an advanced-concept explanation. This documentation does not claim
multidimensional arrays or substantial file-processing logic.

The serializer filters keys containing `api_key`, `secret`, `authorization` or
`prompt`, including nested dictionaries. This is a targeted debug-view rule, not
a guarantee of detecting arbitrary sensitive text. The demo has no real keys.

## Useful tests to discuss

- `tests/test_dashboard_runner.py` checks the runner and resumable runs.
- `tests/test_dashboard_view.py::test_empty_views_and_raw_state_are_safe_and_redacted`
  checks empty views and nested dictionary redaction.
- `tests/test_human_interrupt.py::test_resume_does_not_rerun_analysts_or_decision`
  checks that a human response resumes rather than repeats analysis.
- `tests/test_streamlit_app.py` checks initial loading, validation, approval,
  rejection and navigation around a pending run.
- `tests/test_risk.py` checks rules independently of the UI.

Observed validation results belong in root `TESTING.md`. Test existence alone is
not a claim that every platform or optional API was exercised.

## Libraries and attribution

Streamlit provides the interface, LangGraph provides graph scheduling and
checkpoint interrupts, Pydantic provides validation, and pytest provides the test
framework. Optional SDKs are listed in `requirements.txt`. Their internal
implementations are not claimed as student-written code. The project's nodes,
routing, views, service boundaries and tests connect them into this application.

The interface was developed using the installed `design-taste-frontend` skill,
adapted to the approved neutral research workspace. `docs/images/overview.png`
shows the running application; earlier generated concepts are not evidence that
code runs.

## AI assistance record

AI tools assisted with project review and Python code changes, dashboard design
and implementation, test preparation and review, documentation drafting, and
organization of this submission copy. The student should review and understand
the final code and use the acknowledgement format required by COMP9001.

The provided rubric does not specify an AI-use policy. This is a factual record
of assistance, not a claim of unaided authorship or a statement that a particular
course policy permits that assistance.
