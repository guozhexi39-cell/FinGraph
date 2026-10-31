"""Interactive command-line demo for FinGraph human approval."""

from uuid import uuid4

from langgraph.types import Command

from config import settings
from graph.builder import build_graph


def main() -> None:
    """Run the mock BUY demo and resume the same graph thread after input."""
    graph = build_graph()
    config = {"configurable": {"thread_id": f"demo-aapl-{uuid4().hex[:8]}"}}
    state = graph.invoke({"ticker": "AAPL", "event_log": []}, config)
    proposal = state["trade_proposal"]
    risk_result = state["risk_result"]

    print("FinGraph\n")
    if settings.USE_REAL_PORTFOLIO_STATE:
        _print_portfolio(state["portfolio_state"])
    print("Decision:")
    _print_proposal(proposal)
    print(f"\nRisk:\n{'PASS' if risk_result.approved else 'FAIL'}")
    if risk_result.violations:
        print(f"Violations: {', '.join(risk_result.violations)}")

    if not risk_result.approved:
        print("\nGraph ended due to risk failure")
        return

    if "__interrupt__" not in state:
        if proposal.action == "HOLD":
            print("\nNo human approval required for HOLD")
        print("Graph completed")
        return

    print("\n--------------------------------")
    print("Human Approval Required")
    print("--------------------------------\n")
    _print_proposal(proposal)
    approved = _read_approval()
    final_state = graph.invoke(Command(resume={"approved": approved}), config)
    print("\nHuman approved trade" if approved else "\nHuman rejected trade")
    if approved:
        execution_result = final_state.get("execution_result")
        if execution_result is None:
            print("Paper execution skipped (paper trading is disabled)")
        else:
            print("\nPaper Execution:")
            print(f"Ticker: {execution_result.ticker}")
            print(f"Action: {execution_result.action}")
            print(f"Quantity: {execution_result.quantity}")
            print(f"Order ID: {execution_result.order_id}")
            print(f"Status: {execution_result.status}")
            print(f"Paper Trade: {execution_result.paper_trade}")
    print("Graph completed")
    print("\nEvent Log")
    for event in final_state["event_log"]:
        print(f"- {event}")


def _print_proposal(proposal: object) -> None:
    """Display the state proposal without exposing any model prompt or credentials."""
    print(f"Ticker: {proposal.ticker}")
    print(f"Action: {proposal.action}")
    print(f"Position Size: {proposal.position_size:.0%}")
    print(f"Entry Price: {proposal.entry_price}")
    print(f"Stop Loss: {proposal.stop_loss}")
    print(f"Take Profit: {proposal.take_profit}")


def _read_approval() -> bool:
    """Read an explicit y/n decision for the currently interrupted graph thread."""
    while True:
        answer = input("Approve trade? [y/n]: ").strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        print("Please enter y or n.")


def _print_portfolio(portfolio: object) -> None:
    """Show a compact normalized portfolio, not an Alpaca raw response."""
    print("Portfolio:")
    print(f"Cash: {portfolio.cash if hasattr(portfolio, 'cash') else portfolio['cash']}")
    total_value = (
        portfolio.total_value if hasattr(portfolio, "total_value") else portfolio["total_value"]
    )
    positions = portfolio.positions if hasattr(portfolio, "positions") else portfolio["positions"]
    print(f"Total Value: {total_value}")
    print(f"Positions: {len(positions)}\n")


if __name__ == "__main__":
    main()
