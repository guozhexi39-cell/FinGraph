# Validation and dependency installation

Validation date: 30 October 2026 (Australia/Sydney).

## Results

- A new virtual environment was created without system site-packages.
- All 73 tested dependency wheels were installed using `--no-index` and
  `--require-hashes`, without using the development project's virtual environment.
- `python -m pip check`: no broken requirements.
- `python -m pytest -q -p no:cacheprovider`: **137 passed**.
- One existing `websockets.legacy` deprecation warning was reported; no test failed.
- A running Streamlit instance was checked in a browser using the default mock
  providers. The overview and holdings screenshots in `docs/images/` show this
  submission copy, including a holding quantity of 100.
- Empty and whitespace-only ticker submissions are covered by regression tests:
  the error persists after rerendering, no graph starts, and Reset clears it.
- The actual mock-data-to-view transformation is tested: quantities are preserved
  and cash plus listed holding values reconciles to the total portfolio value.
- Existing routing, human approval/rejection and duplicate-submission tests pass.
  Broker submission tests use fakes. No real order was placed during validation.

## Tested environment

CPython 3.13.14, Apple Silicon macOS. Main libraries: Streamlit 1.61.1,
LangGraph 1.2.10, Pydantic 2.13.4, OpenAI SDK 2.53.0, alpaca-py 0.43.5 and
pytest 9.1.1. Exact dependency versions are in `requirements.lock.txt`.

The pinned dependency set requires a modern Python; use CPython 3.13.x for
reproduction. It is not advertised as tested on Python 3.11. Online dependency
resolution was checked for Windows x64 CPython 3.13, including conditional
colorama, tzdata and watchdog packages. Windows and Linux runtime behavior was
not tested on those operating systems.

Optional live APIs, current credential validity, live financial data and actual
Alpaca Paper execution were not exercised. They are unnecessary for the default
mock demonstration. A successful test run is not a guarantee of a rubric mark.

## General installation

Use the commands in `README.md`. `requirements.lock.txt` pins the complete tested
common dependency set and includes platform-conditional packages.
`requirements.txt` also lists the eight direct dependencies and constrains their
transitive versions using that lock. Either documented requirements file is
included in the source archive. Online installation downloads the appropriate
wheel for the evaluator's platform; platform instructions alone are not a
cross-platform runtime test.

## Optional bundled offline installation

The delivery folder contains a sibling directory:

```text
9001 final/
  FinGraph/                         # this project
  offline-dependencies/
    macos-arm64-python313/
      *.whl
      requirements.offline.txt
      requirements.offline.txt.sha256
```

This bundle is for **CPython 3.13 on Apple Silicon macOS 15 or newer**. Its
compiled wheels are not a Windows, Linux or Intel Mac installation. The selected
orjson wheel determines the macOS 15 minimum. The archive contains the wheels'
original distribution metadata and license files.

From the `FinGraph` folder, create a new environment and install without a
package-index connection:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --no-index --require-hashes --find-links ../offline-dependencies/macos-arm64-python313 -r ../offline-dependencies/macos-arm64-python313/requirements.offline.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/python -m streamlit run app/streamlit_app.py
```

The hashes validate the bundled wheels, not arbitrary future package files.
Use the online instructions on other platforms or provide a separate compatible
wheel bundle. The standalone source ZIP does not include the 88 MB optional
wheel bundle; supply it separately if the tutor requires offline dependencies.
