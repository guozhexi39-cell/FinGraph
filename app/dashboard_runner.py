"""Boundary between the Streamlit dashboard and the existing FinGraph graph."""

from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID, uuid4

from graph.builder import build_graph
from langgraph.types import Command


@dataclass
class DashboardRun:
    """The state and interrupt information produced by one dashboard run."""

    state: dict[str, Any]
    thread_id: str
    interrupted: bool
    interrupt_payload: dict[str, Any] | None
    run_status: str


class DashboardRunner:
    """Start one existing LangGraph run without duplicating backend logic."""

    def __init__(
        self,
        *,
        graph_factory: Callable[[], Any] = build_graph,
        uuid_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        self._graph_factory = graph_factory
        self._uuid_factory = uuid_factory
        self.graph: Any | None = None
        self._thread_id: str | None = None
        self._interrupted = False

    def start(self, ticker: str) -> DashboardRun:
        """Start a unique graph run and return its state or approval interrupt."""
        symbol = ticker.strip().upper()
        if not symbol:
            raise ValueError("Ticker must not be empty.")

        thread_id = f"dashboard-{self._uuid_factory()}"
        self.graph = self._graph_factory()
        self._thread_id = thread_id
        result = self.graph.invoke(
            {"ticker": symbol, "event_log": []},
            {"configurable": {"thread_id": thread_id}},
        )
        return self._result_to_run(result, thread_id)

    def resume_approval(self, approved: bool) -> DashboardRun:
        """Resume the current approval interrupt without restarting the graph.

        ``Command(resume=...)`` continues the existing checkpointer thread, so
        market-data loading and the analyst/decision nodes are not invoked again.
        """
        if not isinstance(approved, bool):
            raise ValueError("Approval decision must be a boolean.")
        if self.graph is None or self._thread_id is None:
            raise RuntimeError("No dashboard run is available to resume.")
        if not self._interrupted:
            raise RuntimeError("The current dashboard run is not awaiting approval.")

        result = self.graph.invoke(
            Command(resume={"approved": approved}),
            {"configurable": {"thread_id": self._thread_id}},
        )
        return self._result_to_run(result, self._thread_id)

    def _result_to_run(self, result: dict[str, Any], thread_id: str) -> DashboardRun:
        """Normalize one graph result and retain its interruption status."""
        raw_interrupts = result.get("__interrupt__", [])
        payload = _interrupt_payload(raw_interrupts)
        state = {key: value for key, value in result.items() if key != "__interrupt__"}
        interrupted = payload is not None
        self._interrupted = interrupted
        return DashboardRun(
            state=state,
            thread_id=thread_id,
            interrupted=interrupted,
            interrupt_payload=payload,
            run_status="Awaiting Human Approval" if interrupted else "Completed",
        )


def _interrupt_payload(interrupts: list[Any]) -> dict[str, Any] | None:
    """Extract the first safe LangGraph interrupt payload, if the graph paused."""
    if not interrupts:
        return None
    payload = getattr(interrupts[0], "value", None)
    return payload if isinstance(payload, dict) else None
