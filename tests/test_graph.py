"""Integration test for the compiled Milestone 1 LangGraph workflow."""

from langgraph.types import Command

from graph.builder import build_graph


def test_compiled_graph_completes_after_risk_feedback() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-risk-feedback"}}
    interrupted_state = graph.invoke({"ticker": "AAPL", "event_log": []}, config)
    final_state = graph.invoke(Command(resume={"approved": True}), config)

    assert "__interrupt__" in interrupted_state
    assert final_state["risk_result"].approved is True
    assert final_state["human_approval"] is True
    assert final_state["risk_retry_count"] == 1
    assert final_state["trade_proposal"].position_size == 0.08
    assert "fundamental_report" in final_state
    assert "technical_report" in final_state
    assert "news_report" in final_state
    assert "Fundamental agent completed" in final_state["event_log"]
    assert "Technical agent completed" in final_state["event_log"]
    assert "News agent completed" in final_state["event_log"]
    assert "Human approved trade" in final_state["event_log"]
