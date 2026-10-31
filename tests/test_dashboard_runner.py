"""Tests for the Streamlit-to-LangGraph dashboard boundary."""

from types import SimpleNamespace
from uuid import UUID

import pytest
from langgraph.types import Command

from app.dashboard_runner import DashboardRunner


class FakeGraph:
    def __init__(self, result: dict[str, object]) -> None:
        self.result = result
        self.calls: list[tuple[dict[str, object], dict[str, object]]] = []

    def invoke(self, state: dict[str, object], config: dict[str, object]) -> dict[str, object]:
        self.calls.append((state, config))
        return self.result


class ResumableFakeGraph:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []
        self.interrupt_payload = {"ticker": "AAPL", "action": "BUY", "risk_approved": True}

    def invoke(self, value: object, config: dict[str, object]) -> dict[str, object]:
        self.calls.append((value, config))
        if isinstance(value, Command):
            approved = value.resume["approved"]
            return {
                "ticker": "AAPL",
                "human_approval": approved,
                "event_log": ["Human approved trade" if approved else "Human rejected trade"],
            }
        return {
            "ticker": "AAPL",
            "event_log": ["Human approval requested"],
            "__interrupt__": [SimpleNamespace(value=self.interrupt_payload)],
        }


def test_runner_normalizes_ticker_and_captures_interrupt() -> None:
    payload = {"ticker": "AAPL", "action": "BUY", "risk_approved": True}
    graph = FakeGraph(
        {"ticker": "AAPL", "event_log": ["Human approval requested"], "__interrupt__": [SimpleNamespace(value=payload)]}
    )
    runner = DashboardRunner(
        graph_factory=lambda: graph,
        uuid_factory=lambda: UUID("00000000-0000-0000-0000-000000000001"),
    )

    result = runner.start(" aapl ")

    assert graph.calls[0][0]["ticker"] == "AAPL"
    assert result.thread_id == "dashboard-00000000-0000-0000-0000-000000000001"
    assert result.interrupted is True
    assert result.interrupt_payload == payload
    assert result.run_status == "Awaiting Human Approval"
    assert "__interrupt__" not in result.state


def test_runner_rejects_empty_ticker() -> None:
    runner = DashboardRunner(graph_factory=lambda: (_ for _ in ()).throw(AssertionError()))

    with pytest.raises(ValueError, match="Ticker must not be empty"):
        runner.start("   ")


def test_each_new_run_has_a_unique_thread_id() -> None:
    identifiers = iter(
        [
            UUID("00000000-0000-0000-0000-000000000001"),
            UUID("00000000-0000-0000-0000-000000000002"),
        ]
    )
    graphs = [FakeGraph({"ticker": "AAPL"}), FakeGraph({"ticker": "AAPL"})]
    runner = DashboardRunner(
        graph_factory=lambda: graphs.pop(0), uuid_factory=lambda: next(identifiers)
    )

    first = runner.start("AAPL")
    second = runner.start("AAPL")

    assert first.thread_id != second.thread_id
    assert first.run_status == "Completed"
    assert second.interrupted is False


def test_hold_end_is_not_reported_as_human_interrupt() -> None:
    graph = FakeGraph({"ticker": "AAPL", "trade_proposal": {"action": "HOLD"}})
    runner = DashboardRunner(graph_factory=lambda: graph)

    result = runner.start("AAPL")

    assert result.interrupted is False
    assert result.interrupt_payload is None
    assert result.run_status == "Completed"


@pytest.mark.parametrize("approved", [True, False])
def test_runner_resumes_same_thread_with_human_command(approved: bool) -> None:
    graph = ResumableFakeGraph()
    runner = DashboardRunner(
        graph_factory=lambda: graph,
        uuid_factory=lambda: UUID("00000000-0000-0000-0000-000000000003"),
    )

    interrupted = runner.start("AAPL")
    resumed = runner.resume_approval(approved)

    command, config = graph.calls[1]
    assert isinstance(command, Command)
    assert command.resume == {"approved": approved}
    assert config == {"configurable": {"thread_id": interrupted.thread_id}}
    assert resumed.thread_id == interrupted.thread_id
    assert resumed.state["human_approval"] is approved
    assert resumed.interrupted is False


def test_runner_cannot_resume_without_an_active_interrupt() -> None:
    runner = DashboardRunner(graph_factory=lambda: FakeGraph({"ticker": "AAPL"}))

    with pytest.raises(RuntimeError, match="No dashboard run"):
        runner.resume_approval(True)

    runner.start("AAPL")
    with pytest.raises(RuntimeError, match="not awaiting approval"):
        runner.resume_approval(True)


def test_runner_resume_does_not_repeat_analyst_or_decision_events() -> None:
    runner = DashboardRunner()

    interrupted = runner.start("AAPL")
    completed = runner.resume_approval(True)

    for event in (
        "Fundamental agent completed",
        "Technical agent completed",
        "News agent completed",
        "Decision generated with position size 0.15",
        "Decision generated with position size 0.08",
    ):
        assert completed.state["event_log"].count(event) == interrupted.state["event_log"].count(event)
    assert completed.thread_id == interrupted.thread_id
