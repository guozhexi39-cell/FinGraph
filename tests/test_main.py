"""Tests for accurate command-line reporting of terminal graph outcomes."""

from types import SimpleNamespace

import pytest

import main as cli
from schemas import RiskResult, TradeProposal


def _use_result(monkeypatch: pytest.MonkeyPatch, *, action: str, approved: bool) -> None:
    state = {
        "trade_proposal": TradeProposal(
            ticker="AAPL",
            action=action,
            position_size=0.0 if action == "HOLD" else 0.15,
            confidence=0.5,
            reason="Test terminal outcome.",
        ),
        "risk_result": RiskResult(
            approved=approved,
            violations=[] if approved else ["MAX_POSITION_EXCEEDED"],
            checked_rules=["MAX_POSITION_SIZE"],
        ),
    }
    graph = SimpleNamespace(invoke=lambda *_args, **_kwargs: state)
    monkeypatch.setattr(cli, "build_graph", lambda: graph)
    monkeypatch.setattr(cli.settings, "USE_REAL_PORTFOLIO_STATE", False)

    def unexpected_approval() -> bool:
        pytest.fail("A terminal graph outcome must not request human approval.")

    monkeypatch.setattr(cli, "_read_approval", unexpected_approval)


def test_risk_failure_is_not_reported_as_pass_or_hold(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_result(monkeypatch, action="BUY", approved=False)

    cli.main()

    output = capsys.readouterr().out
    assert "Risk:\nFAIL" in output
    assert "Violations: MAX_POSITION_EXCEEDED" in output
    assert "Graph ended due to risk failure" in output
    assert "PASS" not in output
    assert "HOLD" not in output
    assert "Graph completed" not in output


def test_approved_hold_reports_pass_and_completion(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_result(monkeypatch, action="HOLD", approved=True)

    cli.main()

    output = capsys.readouterr().out
    assert "Risk:\nPASS" in output
    assert "No human approval required for HOLD" in output
    assert "Graph completed" in output
    assert "risk failure" not in output
