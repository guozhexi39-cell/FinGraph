"""FinGraph's presentation layer; analysis and execution stay in the graph."""

import sys
from html import escape
from pathlib import Path
from typing import Any, MutableMapping

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.dashboard_runner import DashboardRunner
from app.dashboard_styles import DASHBOARD_CSS
from app.dashboard_view import (
    build_agent_view,
    build_decision_view,
    build_execution_view,
    build_portfolio_view,
    build_risk_view,
    detect_agent_disagreement,
    serializable_state,
)
from config import settings

SESSION_DEFAULTS: dict[str, Any] = {
    "thread_id": None,
    "runner": None,
    "graph": None,
    "latest_state": None,
    "interrupt_payload": None,
    "run_status": "Idle",
    "analysis_error": None,
    "selected_ticker": "AAPL",
    "approval_decision": None,
    "resume_in_progress": False,
    "paper_order_confirmation": False,
    "active_view": "analysis",
    "ticker_draft": "AAPL",
}
NAVIGATION = (
    ("analysis", "Analysis & approval", ":material/analytics:"),
    ("account", "Account overview", ":material/account_balance_wallet:"),
    ("holdings", "Holdings", ":material/pie_chart:"),
    ("execution", "Current execution", ":material/receipt_long:"),
    ("activity", "Run activity", ":material/history:"),
)


def initialize_session_state(session_state: MutableMapping[str, Any]) -> None:
    """Initialize display state without starting a graph or an API request."""
    for key, value in SESSION_DEFAULTS.items():
        session_state.setdefault(key, value)


def reset_dashboard_state(session_state: MutableMapping[str, Any]) -> None:
    """Clear dashboard state only; leave backend configuration unchanged."""
    for key, value in SESSION_DEFAULTS.items():
        session_state[key] = value


def _navigate(view: str) -> None:
    """Navigation only changes the visible page, never the running graph."""
    st.session_state["active_view"] = view


def _remember_ticker() -> None:
    st.session_state["ticker_draft"] = st.session_state["ticker_input"]


def _remember_confirmation() -> None:
    st.session_state["paper_order_confirmation"] = bool(
        st.session_state["_paper_order_confirmation"]
    )


def _reset() -> None:
    # Button callbacks run before widgets are recreated on the next render.
    reset_dashboard_state(st.session_state)
    st.session_state.pop("ticker_input", None)
    st.session_state.pop("_paper_order_confirmation", None)


def main() -> None:
    st.set_page_config(
        page_title="FinGraph Research Dashboard", layout="wide", initial_sidebar_state="auto"
    )
    initialize_session_state(st.session_state)
    st.markdown(f"<style>{DASHBOARD_CSS}</style>", unsafe_allow_html=True)
    _render_sidebar()
    _render_dashboard(st.session_state)


def _render_sidebar() -> None:
    with st.sidebar:
        _html('<div class="fg-brand">FinGraph</div>'
              '<div class="fg-brand-subtitle">Research workspace</div>')
        with st.container(key="navigation"):
            for view, label, icon in NAVIGATION:
                st.button(
                    label, key=f"nav_{view}", icon=icon, width="stretch",
                    type="primary" if st.session_state["active_view"] == view else "secondary",
                    on_click=_navigate, args=(view,),
                )
        with st.container(key="sidebar_status"):
            pending = st.session_state["run_status"] == "Awaiting Human Approval"
            status = "Approval pending" if pending else st.session_state["run_status"]
            _status(status, "is-pending" if pending else _status_class(status))
            state = st.session_state["latest_state"] or {}
            if pending:
                st.caption(f"{state.get('ticker', st.session_state['selected_ticker'])} · Review required")
                st.button("View review", key="view_review", on_click=_navigate, args=("analysis",),
                          type="tertiary", width="stretch")
            st.caption("Paper trading only" if settings.USE_PAPER_TRADING else "Execution disabled")
            if st.session_state["active_view"] != "analysis":
                st.button("Reset dashboard", key="reset_dashboard", on_click=_reset,
                          type="tertiary", width="stretch")


def _render_dashboard(session_state: MutableMapping[str, Any]) -> None:
    state = session_state["latest_state"]
    view = session_state["active_view"]
    if session_state["analysis_error"]:
        st.error(session_state["analysis_error"])
    if view == "account":
        _render_account(state, session_state)
    elif view == "holdings":
        _render_holdings(state)
    elif view == "execution":
        _page_header("Current execution", "Order details from the current run")
        _render_execution(state, session_state["run_status"])
        _render_updated_portfolio(state)
    elif view == "activity":
        _page_header("Run activity", "The current run, its events and its state")
        _render_activity(state, session_state)
    else:
        _render_analysis(state, session_state)


def _page_header(title: str, subtitle: str) -> None:
    with st.container(key="page_header"):
        title_col, meta_col = st.columns([3, 1], vertical_alignment="bottom")
        with title_col:
            st.title(title)
            _html(f'<div class="fg-subtitle">{_e(subtitle)}</div>')
        with meta_col:
            if st.session_state["thread_id"]:
                st.caption(f"Run {_short_thread_id(st.session_state['thread_id'])}")


def _render_analysis(state: dict[str, Any] | None, session: MutableMapping[str, Any]) -> None:
    ticker = state.get("ticker", session["selected_ticker"]) if state else session["selected_ticker"]
    with st.container(key="page_header"):
        heading, controls = st.columns([1.2, 1], vertical_alignment="center", gap="large")
        with heading:
            st.title(f"{ticker} analysis")
            company = (state or {}).get("fundamental_data", {}).get("company_name")
            _html(f'<div class="fg-subtitle">{_e(company or "Research overview")}</div>')
            _status(session["run_status"], _status_class(session["run_status"]))
        with controls:
            with st.container(key="analysis_toolbar"):
                field, run, reset = st.columns([1.05, 1.3, 0.55], vertical_alignment="bottom")
                with field:
                    # A persistent draft survives Streamlit's hidden-widget cleanup.
                    if "ticker_input" not in st.session_state:
                        st.session_state["ticker_input"] = session["ticker_draft"]
                    st.text_input("Ticker", key="ticker_input", on_change=_remember_ticker)
                with run:
                    if st.button(
                        "Run analysis", key="run_analysis", type="primary", width="stretch",
                        disabled=session["run_status"] == "Awaiting Human Approval"
                        or session["resume_in_progress"],
                    ):
                        _start_analysis(session.get("ticker_input", ""))
                        st.rerun()
                with reset:
                    st.button("Reset", key="reset_dashboard", on_click=_reset,
                              type="tertiary", width="stretch")
            if session["thread_id"]:
                st.caption(f"Run {_short_thread_id(session['thread_id'])}")
    with st.container(key="analysis_workspace"):
        decision, approval = st.columns([1.35, 1], gap="large")
        with decision:
            _render_decision_and_risk(state)
        with approval:
            with st.container(key="approval_panel"):
                _render_human_approval(state, session)
    _render_agents(state)
    _render_execution_feedback(state, session)


def _render_decision_and_risk(state: dict[str, Any] | None) -> None:
    view = build_decision_view(state.get("trade_proposal") if state else None)
    _html('<div class="fg-label">Proposed action</div>')
    if view is None:
        _html('<div class="fg-proposal-action">—</div>'
              '<p class="fg-rationale">Run an analysis to review a proposal.</p>')
    else:
        facts = f"{view['position_size_display']} position" if view["action"] != "HOLD" else "No new trade"
        _html(f'<div class="fg-inline-facts"><div class="fg-proposal-action">{_e(view["action"])}</div>'
              f'<div>{_e(facts)}<br>{_e(view["confidence_display"])} confidence</div></div>')
        _html(f'<p class="fg-rationale">{_e(_summary_preview(view["reason"]))}</p>')
        if len(view["reason"]) > 240:
            with st.expander("Decision rationale"):
                st.write(view["reason"])
    with st.container(key="proposal_prices"):
        for col, (label, key) in zip(st.columns(3), (
            ("Entry price", "entry_price"), ("Stop loss", "stop_loss"),
            ("Take profit", "take_profit"),
        )):
            with col:
                _html(f'<div class="fg-label">{label}</div>'
                      f'<div class="fg-price">{_currency(view[key] if view else None)}</div>')
    risk = build_risk_view((state or {}).get("risk_result"), (state or {}).get("risk_retry_count"))
    if risk is None:
        _status("No risk result yet")
    else:
        _status("Risk passed" if risk["approved"] else "Risk rejected",
                "is-positive" if risk["approved"] else "is-negative")
        st.caption(
            f"{'No violations' if risk['approved'] else ', '.join(risk['violations'])}"
            f" · {risk['retry_count']} / {settings.MAX_RISK_RETRY} retries"
        )
        with st.expander("Risk details"):
            st.write("PASS" if risk["approved"] else "REJECTED")
            if risk["violations"]:
                st.write("Violations")
                for violation in risk["violations"]:
                    st.write(violation)
            st.write("Checked rules")
            st.write(risk["checked_rules"])
            st.write(f"Decision Retry: {risk['retry_count']} / {settings.MAX_RISK_RETRY}")


def _render_agents(state: dict[str, Any] | None) -> None:
    with st.container(key="agent_reports"):
        st.header("Analyst perspectives")
        reports = (("Fundamental", "fundamental_report"),
                   ("Technical", "technical_report"), ("News", "news_report"))
        for col, (name, key) in zip(st.columns(3, gap="large"), reports):
            with col:
                _html(f'<div class="fg-agent-name">{name}</div>')
                view = build_agent_view((state or {}).get(key))
                if view is None:
                    st.caption("No analysis run yet")
                    continue
                signal = view["signal"].title()
                color = {"BULLISH": "is-positive", "BEARISH": "is-negative"}.get(view["signal"], "")
                _status(f"{signal} · {view['confidence_display']} confidence", color)
                _html(f'<p class="fg-agent-summary">{_e(_summary_preview(view["summary"]))}</p>')
                with st.expander("Evidence & risks"):
                    st.write("Summary")
                    st.write(view["summary"])
                    st.write("Evidence")
                    for evidence in view["evidence"]:
                        st.write(evidence)
                    st.write("Risks")
                    for risk in view["risks"]:
                        st.write(risk)
        disagreement = detect_agent_disagreement(state or {})
        if disagreement["signals"]:
            signals = "; ".join(f"{name.lower()} {signal}" for name, signal in disagreement["signals"].items())
            st.caption(f"{'Mixed signals' if disagreement['detected'] else 'Agents broadly agree'}: {signals}.")


def _render_human_approval(state: dict[str, Any] | None, session: MutableMapping[str, Any]) -> None:
    st.header("Human approval")
    proposal = (state or {}).get("trade_proposal")
    action = _value(proposal, "action") if proposal is not None else None
    risk = (state or {}).get("risk_result")
    eligible = _value(risk, "approved") is True if risk else False
    payload = session["interrupt_payload"]
    if action == "HOLD":
        st.info("No human approval required for HOLD.")
    elif action in {"BUY", "SELL"} and payload and eligible:
        _render_approval_details(payload)
        _render_approval_controls(session)
    elif proposal is None:
        st.caption("No approval state yet")
        st.caption("Run an analysis to review a risk-checked proposal here.")
    elif risk and not eligible:
        st.info("Trade is not eligible for human approval because Risk rejected it.")
    elif session["run_status"] == "Rejected by Human":
        _status("Rejected by human")
        st.caption("No order submitted.")
    else:
        st.info("No human approval request")


def _render_approval_details(payload: dict[str, Any]) -> None:
    size = payload.get("position_size")
    position = f" · {float(size):.0%}" if size is not None else ""
    _html(f'<div class="fg-review-summary">{_e(payload.get("ticker", "—"))} · '
          f'{_e(payload.get("action", "—"))}{position}</div>')
    with st.expander("Trade details"):
        for label, key in (("Entry price", "entry_price"), ("Stop loss", "stop_loss"),
                           ("Take profit", "take_profit"), ("Confidence", "confidence")):
            if payload.get(key) is not None:
                st.write(f"{label}: {payload[key]}")
        st.write("Reason")
        st.write(payload.get("reason", "—"))


def _render_approval_controls(session: MutableMapping[str, Any]) -> None:
    resume_in_progress = bool(session["resume_in_progress"])
    already_submitted = session["approval_decision"] is not None
    approve_label = "Approve"
    approve_disabled = resume_in_progress or already_submitted
    if settings.USE_PAPER_TRADING:
        st.warning("PAPER TRADING ONLY")
        st.caption("No real funds are used.")
        # Keep the durable confirmation separate from the disposable widget key.
        if "_paper_order_confirmation" not in st.session_state:
            st.session_state["_paper_order_confirmation"] = bool(session["paper_order_confirmation"])
        st.checkbox(
            "I confirm this is a Paper Trading order.", key="_paper_order_confirmation",
            on_change=_remember_confirmation, disabled=resume_in_progress,
        )
        approve_label = "Approve & Submit Paper Order"
        approve_disabled = resume_in_progress or already_submitted or not bool(session["paper_order_confirmation"])
    approved = st.button(approve_label, key="approve_trade", type="primary",
                         disabled=approve_disabled, width="stretch")
    rejected = st.button("Reject", key="reject_trade", disabled=resume_in_progress or already_submitted,
                         width="stretch")
    if settings.USE_PAPER_TRADING and not session["paper_order_confirmation"]:
        st.caption("Confirm paper trading to enable approval.")
    if approved:
        _resume_approval(True)
        st.rerun()
    if rejected:
        _resume_approval(False)
        st.rerun()


def _render_execution_feedback(state: dict[str, Any] | None, session: MutableMapping[str, Any]) -> None:
    """Keep the current run's outcome visible next to its analysis."""
    if not state or session["interrupt_payload"]:
        return
    if session["run_status"] == "Rejected by Human":
        st.info("Trade rejected by human. No order submitted.")
        st.info("Not executed")
    else:
        execution = build_execution_view(state.get("execution_result"))
        if execution and execution["status"].lower() in {"accepted", "new", "pending_new"}:
            st.info("Order submitted; not filled yet.")
        elif execution:
            st.caption(f"Execution: {execution['status']}")
        elif session["run_status"] == "Completed":
            st.info("Not executed")


def _render_account(state: dict[str, Any] | None, session: MutableMapping[str, Any]) -> None:
    _page_header("Account overview", "Alpaca Paper account" if settings.USE_REAL_PORTFOLIO_STATE else "Mock portfolio")
    _render_portfolio_metrics(state)
    if state and state.get("portfolio_state"):
        st.button("View holdings →", key="account_view_holdings", type="tertiary",
                  on_click=_navigate, args=("holdings",))
    else:
        st.info("No portfolio loaded. Run an analysis to load the current portfolio.")
    with st.container(key="account_details"):
        modes, review = st.columns([1.65, 1], gap="large")
        with modes:
            st.header("Operating modes")
            rows = (
                ("Market data", _mode(settings.USE_REAL_MARKET_DATA)),
                ("Fundamentals", _mode(settings.USE_REAL_FUNDAMENTAL_DATA)),
                ("News data", _mode(settings.USE_REAL_NEWS_DATA)),
                ("Analyst model", "DeepSeek" if settings.USE_REAL_ANALYST_LLM else "Mock"),
                ("Decision model", "DeepSeek" if settings.USE_REAL_DECISION_LLM else "Mock"),
                ("Portfolio source", "Alpaca Paper" if settings.USE_REAL_PORTFOLIO_STATE else "Mock"),
                ("Execution mode", "Paper trading" if settings.USE_PAPER_TRADING else "Disabled"),
            )
            _key_values(rows)
        with review:
            proposal = build_decision_view((state or {}).get("trade_proposal"))
            if proposal:
                with st.container(key="current_review"):
                    st.subheader("Current review")
                    _html(f'<div class="fg-review-summary">{_e(proposal["ticker"])} · '
                          f'{_e(proposal["action"])} · {_e(proposal["position_size_display"])}</div>')
                    _status(session["run_status"], _status_class(session["run_status"]))
                    if not (state or {}).get("execution_result"):
                        if session["run_status"] == "Failed" and session["approval_decision"] is True:
                            st.warning("Execution status unavailable. Review the paper account before retrying.")
                        else:
                            st.caption("No order submitted.")
                    st.button("View review", key="account_view_review", on_click=_navigate,
                              args=("analysis",), width="stretch")


def _render_portfolio_metrics(state: dict[str, Any] | None) -> None:
    portfolio = (state or {}).get("portfolio_state")
    view = build_portfolio_view(portfolio)
    with st.container(key="portfolio_metrics"):
        total, cash, count = st.columns([1.45, 1, 0.8], gap="large")
        for col, label, value, lead in (
            (total, "Portfolio value", _currency(view["total_value"]), True),
            (cash, "Available cash", _currency(view["cash"]), False),
            (count, "Open positions", str(view["position_count"]) if portfolio else "—", False),
        ):
            with col:
                _html(f'<div class="fg-label">{label}</div><div class="fg-portfolio-value'
                      f'{" is-lead" if lead else ""}">{_e(value)}</div>')


def _render_holdings(state: dict[str, Any] | None) -> None:
    _page_header("Holdings", "Current paper-account positions" if settings.USE_REAL_PORTFOLIO_STATE else "Current mock portfolio positions")
    view = build_portfolio_view((state or {}).get("portfolio_state"))
    count, account = st.columns([3, 1])
    with count:
        st.write(f"{view['position_count']} open positions" if state else "No portfolio loaded")
    with account:
        st.button("Account overview →", key="holdings_view_account", type="tertiary",
                  on_click=_navigate, args=("account",), width="stretch")
    _render_holdings_table(state)


def _render_holdings_table(state: dict[str, Any] | None) -> None:
    view = build_portfolio_view((state or {}).get("portfolio_state"))
    if not view["positions"]:
        st.info("No open positions" if (state or {}).get("portfolio_state") else "Run an analysis to load portfolio information.")
        return
    st.dataframe(
        view["positions"], hide_index=True, width="stretch", row_height=56,
        column_config={
            "Ticker": st.column_config.TextColumn("Stock"),
            "Quantity": st.column_config.NumberColumn("Quantity", format="compact"),
            "Market Value": st.column_config.NumberColumn("Market value", format="dollar"),
            "Position Size": st.column_config.TextColumn("Portfolio weight"),
        },
    )
    total = sum(float(position["Market Value"]) for position in view["positions"])
    _key_values((("Total market value", _currency(total)),))
    st.caption("Weights are based on the total portfolio, including cash.")


def _render_execution(state: dict[str, Any] | None, run_status: str) -> None:
    st.header("Execution")
    view = build_execution_view((state or {}).get("execution_result"))
    if view is None:
        if run_status == "Failed" and st.session_state["approval_decision"] is True:
            st.warning("Execution status unavailable. Review the paper account before retrying.")
            return
        if run_status == "Rejected by Human":
            st.info("Trade rejected by human. No order submitted.")
        elif run_status == "Awaiting Human Approval":
            _status("Awaiting approval", "is-pending")
            st.caption("No order submitted.")
        st.info("Not executed")
        return
    _key_values((
        ("Ticker", view["ticker"]), ("Action", view["action"]),
        ("Quantity", view["quantity"]), ("Order ID", view["order_id"]),
        ("Status", view["status"]), ("Paper trade", str(view["paper_trade"])),
        ("Submitted at", view["submitted_at"] or "—"),
        ("Filled at", view["filled_at"] or "—"),
        ("Filled price", _currency(view["filled_price"])),
    ))
    if view["status"].lower() in {"accepted", "new", "pending_new"}:
        st.info("Order submitted; not filled yet.")


def _render_updated_portfolio(state: dict[str, Any] | None) -> None:
    with st.container(key="updated_portfolio"):
        st.header("Updated portfolio")
        _render_portfolio_metrics(state)
        _render_holdings_table(state)


def _render_activity(state: dict[str, Any] | None, session: MutableMapping[str, Any]) -> None:
    _key_values((("Run status", session["run_status"]),
                 ("Ticker", (state or {}).get("ticker", session["selected_ticker"])),
                 ("Thread", session["thread_id"] or "—")))
    _render_event_log(state)
    _render_raw_state(state)
    with st.expander("Environment"):
        for line in _environment_lines():
            st.write(line)


def _render_event_log(state: dict[str, Any] | None) -> None:
    with st.expander("Event log", expanded=True):
        events = (state or {}).get("event_log", [])
        if events:
            for event in events:
                st.write(f"- {event}")
        else:
            st.info("No events yet")


def _render_raw_state(state: dict[str, Any] | None) -> None:
    with st.expander("Advanced / Debug"):
        st.json(serializable_state(state))


def _key_values(rows: Any) -> None:
    _html('<dl class="fg-key-values">' + ''.join(
        f'<div><dt>{_e(label)}</dt><dd>{_e(value)}</dd></div>' for label, value in rows
    ) + '</dl>')


def _status(label: str, css_class: str = "") -> None:
    _html(f'<div class="fg-status"><span class="fg-dot {css_class}"></span>{_e(label)}</div>')


def _status_class(status: str) -> str:
    return {"Awaiting Human Approval": "is-pending", "Running": "is-pending",
            "Completed": "is-positive", "Failed": "is-negative"}.get(status, "")


def _summary_preview(summary: str) -> str:
    return summary if len(summary) <= 240 else summary[:237].rsplit(" ", 1)[0] + "…"


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _e(value: Any) -> str:
    return escape(str(value), quote=True)


def _mode(real: bool) -> str:
    return "REAL" if real else "MOCK"


def _environment_lines() -> list[str]:
    data_is_real = any((settings.USE_REAL_MARKET_DATA, settings.USE_REAL_FUNDAMENTAL_DATA, settings.USE_REAL_NEWS_DATA))
    return [
        f"DATA: {'REAL' if data_is_real else 'MOCK'}",
        f"ANALYSTS: {'DEEPSEEK' if settings.USE_REAL_ANALYST_LLM else 'MOCK'}",
        f"DECISION: {'DEEPSEEK' if settings.USE_REAL_DECISION_LLM else 'MOCK'}",
        f"PORTFOLIO: {'ALPACA PAPER' if settings.USE_REAL_PORTFOLIO_STATE else 'MOCK'}",
        f"EXECUTION: {'PAPER' if settings.USE_PAPER_TRADING else 'DISABLED'}",
    ]


def _short_thread_id(thread_id: str | None) -> str:
    return thread_id.rsplit("-", 1)[-1][:8] if thread_id else "—"


def _currency(value: float | None) -> str:
    return "—" if value is None else f"${value:,.2f}"


def _value(item: Any, field: str) -> Any:
    if isinstance(item, dict):
        return item.get(field)
    return getattr(item, field, None)


# Keep graph execution behind the explicit run and approval controls.
def _start_analysis(ticker: str) -> None:
    symbol = ticker.strip().upper()
    if not symbol:
        st.session_state["analysis_error"] = "Ticker must not be empty."
        return
    runner = DashboardRunner()
    try:
        st.session_state["run_status"] = "Running"
        with st.spinner("Running FinGraph..."):
            result = runner.start(symbol)
    except Exception as error:
        st.session_state["latest_state"] = None
        st.session_state["interrupt_payload"] = None
        st.session_state["run_status"] = "Failed"
        st.session_state["analysis_error"] = f"Analysis failed: {error}"
        return

    st.session_state["runner"] = runner
    st.session_state["graph"] = runner.graph
    st.session_state["thread_id"] = result.thread_id
    st.session_state["latest_state"] = result.state
    st.session_state["interrupt_payload"] = result.interrupt_payload
    st.session_state["run_status"] = result.run_status
    st.session_state["analysis_error"] = None
    st.session_state["selected_ticker"] = symbol
    st.session_state["approval_decision"] = None
    st.session_state["resume_in_progress"] = False
    st.session_state["paper_order_confirmation"] = False


def _resume_approval(approved: bool) -> None:
    """Resume exactly one existing interrupt; the dashboard never submits orders."""
    if (
        st.session_state["resume_in_progress"]
        or st.session_state["approval_decision"] is not None
        or not st.session_state["interrupt_payload"]
    ):
        return
    runner = st.session_state["runner"]
    if runner is None:
        st.session_state["analysis_error"] = "No interrupted graph run is available to resume."
        return

    st.session_state["resume_in_progress"] = True
    st.session_state["approval_decision"] = approved
    try:
        with st.spinner("Resuming approved trade..." if approved else "Rejecting trade..."):
            result = runner.resume_approval(approved)
    except Exception as error:
        st.session_state["run_status"] = "Failed"
        st.session_state["analysis_error"] = (
            f"Paper execution failed: {error}" if approved else f"Resume failed: {error}"
        )
        return
    finally:
        st.session_state["resume_in_progress"] = False

    st.session_state["thread_id"] = result.thread_id
    st.session_state["latest_state"] = result.state
    st.session_state["interrupt_payload"] = result.interrupt_payload
    st.session_state["analysis_error"] = None
    if result.interrupted:
        st.session_state["run_status"] = result.run_status
        st.session_state["approval_decision"] = None
    elif approved:
        st.session_state["run_status"] = "Completed"
    else:
        st.session_state["run_status"] = "Rejected by Human"

if __name__ == "__main__":
    main()
