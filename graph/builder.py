"""LangGraph topology for the FinGraph simulated trading flow."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, START, StateGraph

from graph.routing import route_after_human_approval, route_after_risk
from graph.state import TradingState
from nodes.decision_agent import decision_agent_node
from nodes.execution_node import execution_node
from nodes.fundamental_agent import fundamental_agent_node
from nodes.human_approval import (
    hold_completion_node,
    human_approval_node,
    human_approval_request_node,
)
from nodes.mock_data import mock_data_node
from nodes.news_agent import news_agent_node
from nodes.portfolio_sync import portfolio_refresh_node, portfolio_sync_node
from nodes.risk_engine import risk_engine_node
from nodes.technical_agent import technical_agent_node


def build_graph(*, checkpointer: MemorySaver | None = None):
    """Compile the workflow with an in-memory checkpointer for human resume.

    The list-form edge creates a fan-in barrier: the decision node runs only
    after all three analyst branches have produced their reports. A unique
    ``thread_id`` supplied at invocation time identifies the resumable run.
    """
    workflow = StateGraph(TradingState)
    workflow.add_node("mock_data", mock_data_node)
    workflow.add_node("portfolio_sync", portfolio_sync_node)
    workflow.add_node("fundamental_agent", fundamental_agent_node)
    workflow.add_node("technical_agent", technical_agent_node)
    workflow.add_node("news_agent", news_agent_node)
    workflow.add_node("decision_agent", decision_agent_node)
    workflow.add_node("risk_engine", risk_engine_node)
    workflow.add_node("human_approval_request", human_approval_request_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("hold_completion", hold_completion_node)
    workflow.add_node("execution_node", execution_node)
    workflow.add_node("portfolio_refresh", portfolio_refresh_node)

    workflow.add_edge(START, "mock_data")
    workflow.add_edge("mock_data", "portfolio_sync")
    workflow.add_edge("portfolio_sync", "fundamental_agent")
    workflow.add_edge("portfolio_sync", "technical_agent")
    workflow.add_edge("portfolio_sync", "news_agent")
    workflow.add_edge(
        ["fundamental_agent", "technical_agent", "news_agent"], "decision_agent"
    )
    workflow.add_edge("decision_agent", "risk_engine")
    workflow.add_conditional_edges(
        "risk_engine",
        route_after_risk,
        {
            "human_approval": "human_approval_request",
            "hold": "hold_completion",
            "retry": "decision_agent",
            "abort": END,
        },
    )
    workflow.add_edge("human_approval_request", "human_approval")
    workflow.add_conditional_edges(
        "human_approval",
        route_after_human_approval,
        {"execute": "execution_node", "end": END},
    )
    workflow.add_edge("execution_node", "portfolio_refresh")
    workflow.add_edge("portfolio_refresh", END)
    workflow.add_edge("hold_completion", END)

    saver = checkpointer or MemorySaver(
        serde=JsonPlusSerializer(
            allowed_msgpack_modules=[
                ("schemas.analyst_report", "AnalystReport"),
                ("schemas.execution", "ExecutionResult"),
                ("schemas.portfolio", "PortfolioState"),
                ("schemas.risk", "RiskResult"),
                ("schemas.trade_proposal", "TradeProposal"),
            ]
        )
    )
    return workflow.compile(checkpointer=saver)
