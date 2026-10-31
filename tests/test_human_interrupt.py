"""Tests for LangGraph human approval interrupt and resume behavior."""

import pytest
from langgraph.types import Command

from graph import builder
from schemas import TradeProposal


def _config(name: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": name}}


def _interrupt(graph: object, config: dict[str, object]) -> dict[str, object]:
    return graph.invoke({"ticker": "AAPL", "event_log": []}, config)


def test_buy_after_risk_pass_interrupts_with_safe_trade_payload() -> None:
    graph = builder.build_graph()
    state = _interrupt(graph, _config("human-payload"))

    payload = state["__interrupt__"][0].value
    assert payload == {
        "ticker": "AAPL",
        "action": "BUY",
        "position_size": 0.08,
        "entry_price": 210.0,
        "stop_loss": 200.0,
        "take_profit": 230.0,
        "confidence": 0.72,
        "reason": "Position size reduced after risk feedback.",
        "risk_approved": True,
    }
    assert graph.get_state(_config("human-payload")).next == ("human_approval",)
    assert "Human approval requested" in state["event_log"]


@pytest.mark.parametrize(
    ("approved", "event"),
    [(True, "Human approved trade"), (False, "Human rejected trade")],
)
def test_resume_records_the_human_decision(approved: bool, event: str) -> None:
    graph = builder.build_graph()
    config = _config(f"human-{approved}")
    _interrupt(graph, config)

    final_state = graph.invoke(Command(resume={"approved": approved}), config)

    assert final_state["human_approval"] is approved
    assert event in final_state["event_log"]
    if not approved:
        assert final_state["event_log"][-1] == event
    assert "__interrupt__" not in final_state


def test_resume_does_not_rerun_analysts_or_decision() -> None:
    graph = builder.build_graph()
    config = _config("human-no-rerun")
    interrupted = _interrupt(graph, config)
    events_before_resume = interrupted["event_log"]

    final_state = graph.invoke(Command(resume={"approved": True}), config)

    for event in (
        "Fundamental agent completed",
        "Technical agent completed",
        "News agent completed",
    ):
        assert final_state["event_log"].count(event) == events_before_resume.count(event) == 1
    assert final_state["event_log"].count("Decision generated with position size 0.15") == 1
    assert final_state["event_log"].count("Decision generated with position size 0.08") == 1


def test_hold_completes_without_human_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    def hold_decision(state: dict[str, object]) -> dict[str, object]:
        return {
            "trade_proposal": TradeProposal(
                ticker="AAPL",
                action="HOLD",
                position_size=0.0,
                confidence=0.4,
                reason="Mixed signals.",
            ),
            "event_log": [*state.get("event_log", []), "Test HOLD decision"],
        }

    monkeypatch.setattr(builder, "decision_agent_node", hold_decision)
    graph = builder.build_graph()

    final_state = _interrupt(graph, _config("hold-no-interrupt"))

    assert "__interrupt__" not in final_state
    assert final_state["human_approval"] is None
    assert "No human approval required for HOLD" in final_state["event_log"]
    assert "Human approval requested" not in final_state["event_log"]


def test_risk_reject_does_not_enter_human_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def oversized_decision(state: dict[str, object]) -> dict[str, object]:
        return {
            "trade_proposal": TradeProposal(
                ticker="AAPL",
                action="BUY",
                position_size=0.15,
                entry_price=210.0,
                stop_loss=200.0,
                take_profit=230.0,
                confidence=0.5,
                reason="Deliberately rejected test proposal.",
            ),
            "event_log": [*state.get("event_log", []), "Test oversized decision"],
        }

    monkeypatch.setattr(builder, "decision_agent_node", oversized_decision)
    graph = builder.build_graph()

    final_state = _interrupt(graph, _config("risk-reject-no-interrupt"))

    assert "__interrupt__" not in final_state
    assert final_state["risk_result"].approved is False
    assert final_state["risk_retry_count"] == 2
    assert "Human approval requested" not in final_state["event_log"]
