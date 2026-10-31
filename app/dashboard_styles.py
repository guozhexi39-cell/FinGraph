"""Presentation styles for the approved FinGraph research workspace.

``DASHBOARD_CSS`` contains CSS only. Wrap it in a style element when rendering
with Streamlit; importing this module performs no UI or application actions.
The native Streamlit sidebar toggle, controls and interaction states stay intact.
"""

DASHBOARD_CSS = r"""
:root {
  --fg-font: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Segoe UI", sans-serif;
  --fg-ink: #111113;
  --fg-secondary: #55555e;
  --fg-muted: #62626b;
  --fg-paper: #ffffff;
  --fg-sidebar: #f5f5f7;
  --fg-panel: #f5f5f7;
  --fg-active: #e6e6eb;
  --fg-rule: #e8e8ec;
  --fg-control: #c5c5cd;
  --fg-positive: #227945;
  --fg-negative: #b42332;
  --fg-pending: #e79a13;
}

[data-testid="stApp"],
[data-testid="stAppViewContainer"] {
  background: var(--fg-paper);
  color: var(--fg-ink);
  font-family: var(--fg-font);
  -webkit-font-smoothing: antialiased;
}

[data-testid="stMainBlockContainer"] {
  max-width: 1400px;
  padding: 76px 48px 48px;
}

[data-testid="stMain"] {
  background: var(--fg-paper);
}

/* Keep the native sidebar controls; only deployment and toolbar chrome recedes. */
[data-testid="stHeader"] {
  background: transparent;
  box-shadow: none;
}
[data-testid="stAppDeployButton"],
[data-testid="stToolbarActions"],
[data-testid="stMainMenu"],
[data-testid="stDecoration"] {
  display: none;
}
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
  color: var(--fg-ink);
  z-index: 100;
}

/* Sidebar: the product name and one quiet navigation list. */
[data-testid="stSidebar"] {
  width: 255px !important;
  min-width: 255px !important;
  max-width: 255px !important;
  background: var(--fg-sidebar);
  border-right: 1px solid var(--fg-rule);
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
  padding: 12px 14px 24px;
}
[data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
  min-height: calc(100dvh - 86px);
}
.fg-brand {
  margin: 0;
  padding: 0 14px;
  color: var(--fg-ink);
  font: 650 28px/1.15 var(--fg-font);
  letter-spacing: -0.055em;
}
.fg-brand-subtitle {
  margin: 5px 0 0;
  padding: 0 14px;
  color: var(--fg-muted);
  font: 400 14px/1.5 var(--fg-font);
}
.st-key-navigation {
  margin-top: 22px;
}
[data-testid="stSidebar"] .st-key-navigation [data-testid="stButton"] {
  margin: 0;
}
[data-testid="stSidebar"] .st-key-navigation button {
  min-height: 48px;
  width: 100%;
  padding: 10px 14px;
  justify-content: flex-start;
  gap: 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #363640;
  box-shadow: none;
  font: 400 16px/1.45 var(--fg-font);
  text-align: left;
  transition: background-color 140ms ease, color 140ms ease;
}
[data-testid="stSidebar"] .st-key-navigation button:hover {
  background: #ededf0;
  color: var(--fg-ink);
}
[data-testid="stSidebar"] .st-key-navigation button[kind="primary"],
[data-testid="stSidebar"] .st-key-navigation button[data-testid="baseButton-primary"],
[data-testid="stSidebar"] .st-key-navigation button[data-testid="stBaseButton-primary"] {
  background: var(--fg-active);
  color: var(--fg-ink);
  font-weight: 500;
}
[data-testid="stSidebar"] .st-key-navigation button p {
  font-family: var(--fg-font);
  font-size: 16px;
  line-height: 1.45;
  text-align: left;
}
[data-testid="stSidebar"] .st-key-navigation [data-testid="stIconMaterial"] {
  font-size: 21px;
  font-variation-settings: "FILL" 0, "wght" 350;
}
.st-key-sidebar_status {
  margin-top: auto;
  margin-right: 12px;
  margin-left: 12px;
  padding-top: 20px;
  border-top: 1px solid #dedee5;
}
.st-key-sidebar_status .fg-status {
  font-size: 14px;
}
.st-key-sidebar_status .fg-subtitle,
.st-key-sidebar_status [data-testid="stCaptionContainer"] p {
  color: var(--fg-muted);
  font-size: 13px;
  line-height: 1.55;
}
.st-key-sidebar_status button {
  justify-content: flex-start;
  padding-right: 0;
  padding-left: 0;
  border: 0;
  background: transparent;
  color: var(--fg-secondary);
  font-size: 14px;
}

/* Main frame: 48 px gutters; native columns keep Streamlit's own proportions. */
.st-key-page_header {
  margin-bottom: 34px;
}
.fg-page-title {
  margin: 0 0 5px;
  color: var(--fg-ink);
  font: 650 40px/1.14 var(--fg-font);
  letter-spacing: -0.045em;
  overflow-wrap: anywhere;
}
.fg-subtitle {
  margin: 0;
  color: var(--fg-secondary);
  font: 400 18px/1.5 var(--fg-font);
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h2:not([class]) {
  margin-top: 0;
  padding-top: 0;
  color: var(--fg-ink);
  font-size: 26px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.035em;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] h3:not([class]) {
  margin-top: 0;
  padding-top: 0;
  color: var(--fg-ink);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: -0.02em;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p:not([class]),
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li {
  font-family: var(--fg-font);
  line-height: 1.6;
}
[data-testid="stMain"] [data-testid="stCaptionContainer"] p {
  color: var(--fg-muted);
  font: 400 14px/1.55 var(--fg-font);
}

/* Toolbar controls are the existing ticker, run and reset interactions. */
.st-key-analysis_toolbar [data-testid="stHorizontalBlock"] {
  align-items: flex-end;
  gap: 12px;
}
.st-key-analysis_toolbar label p {
  color: var(--fg-muted);
  font-size: 14px;
}
[data-testid="stMain"] [data-testid="stTextInput"] input {
  min-height: 44px;
  color: var(--fg-ink);
  font: 400 16px/1.4 var(--fg-font);
}
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"] {
  min-height: 44px;
  border: 1px solid var(--fg-control);
  border-radius: 7px;
  background: var(--fg-paper);
  box-shadow: none;
}
[data-testid="stMain"] [data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
  border-color: #656570;
  outline: 2px solid #b8cfea;
  outline-offset: 2px;
}
[data-testid="stMain"] [data-testid="stButton"] button {
  min-height: 44px;
  border: 1px solid var(--fg-control);
  border-radius: 7px;
  background: var(--fg-paper);
  color: var(--fg-secondary);
  box-shadow: none;
  font: 400 15px/1.4 var(--fg-font);
  transition: background-color 140ms ease, border-color 140ms ease;
}
[data-testid="stMain"] [data-testid="stButton"] button:hover:not(:disabled) {
  border-color: #8b8b95;
  background: #f5f5f7;
  color: var(--fg-ink);
}
[data-testid="stMain"] [data-testid="stButton"] button[kind="primary"],
[data-testid="stMain"] [data-testid="stButton"] button[data-testid="baseButton-primary"],
[data-testid="stMain"] [data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
  border-color: #1d1d1f;
  background: #1d1d1f;
  color: #ffffff;
}
[data-testid="stMain"] [data-testid="stButton"] button[kind="primary"]:hover:not(:disabled),
[data-testid="stMain"] [data-testid="stButton"] button[data-testid="baseButton-primary"]:hover:not(:disabled),
[data-testid="stMain"] [data-testid="stButton"] button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
  border-color: #37373b;
  background: #37373b;
  color: #ffffff;
}
[data-testid="stMain"] [data-testid="stButton"] button:disabled {
  border-color: transparent;
  background: #e3e3e8;
  color: #61616b;
  opacity: 1;
  cursor: not-allowed;
}
[data-testid="stMain"] [data-testid="stButton"] button:focus-visible,
[data-testid="stSidebar"] button:focus-visible {
  outline: 2px solid #477cb3;
  outline-offset: 3px;
}
.st-key-reset_dashboard button {
  border-color: transparent !important;
  background: transparent !important;
  color: var(--fg-ink) !important;
}

/* Proposal and approval are the primary reading pair, without extra card chrome. */
.fg-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 0;
  color: #363640;
  font: 400 15px/1.5 var(--fg-font);
}
.fg-dot {
  display: inline-block;
  flex: 0 0 10px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #8d8d97;
}
.fg-dot.is-pending,
.fg-status.is-pending .fg-dot { background: var(--fg-pending); }
.fg-dot.is-positive,
.fg-status.is-positive .fg-dot { background: var(--fg-positive); }
.fg-dot.is-negative,
.fg-status.is-negative .fg-dot { background: var(--fg-negative); }
.fg-label {
  margin: 0 0 7px;
  color: var(--fg-secondary);
  font: 400 16px/1.45 var(--fg-font);
}
.fg-proposal-action {
  margin: 0;
  color: #08080a;
  font: 650 80px/1 var(--fg-font);
  letter-spacing: -0.055em;
}
.fg-inline-facts {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--fg-ink);
  font: 400 20px/1.35 var(--fg-font);
  font-variant-numeric: tabular-nums;
}
.fg-rationale {
  max-width: 680px;
  margin: 18px 0 28px;
  color: #43434d;
  font: 400 17px/1.6 var(--fg-font);
}
.fg-price {
  margin: 3px 0 0;
  color: var(--fg-ink);
  font: 400 28px/1.25 var(--fg-font);
  letter-spacing: -0.035em;
  font-variant-numeric: tabular-nums;
}
.st-key-approval_panel {
  padding: 24px;
  border: 0;
  border-radius: 18px;
  background: var(--fg-panel);
}
.st-key-approval_panel [data-testid="stCheckbox"] label {
  min-height: 44px;
  align-items: center;
}
.st-key-approval_panel [data-testid="stCheckbox"] label p {
  color: #43434d;
  font-size: 15px;
  line-height: 1.5;
}
.st-key-approval_panel [data-testid="stButton"] button {
  min-height: 46px;
  width: 100%;
}
.st-key-approval_panel [data-testid="stCaptionContainer"] p {
  color: var(--fg-muted);
  font-size: 13px;
}

/* Analyst summaries remain open; native expanders retain their detail controls. */
.fg-agent-name {
  margin: 0 0 6px;
  color: var(--fg-ink);
  font: 600 19px/1.35 var(--fg-font);
  letter-spacing: -0.02em;
}
.fg-agent-meta {
  display: flex;
  align-items: center;
  gap: 9px;
  margin: 0 0 10px;
  color: var(--fg-muted);
  font: 400 14px/1.5 var(--fg-font);
}
.fg-agent-summary {
  margin: 0 0 10px;
  color: var(--fg-secondary);
  font: 400 14px/1.65 var(--fg-font);
}
[data-testid="stMain"] [data-testid="stExpander"] details {
  border: 0;
  border-radius: 0;
  background: var(--fg-paper);
}
[data-testid="stMain"] [data-testid="stExpander"] summary {
  min-height: 44px;
  padding-right: 0;
  padding-left: 0;
  color: #43434d;
}
[data-testid="stMain"] [data-testid="stExpander"] summary p {
  font-size: 14px;
}

/* Account figures and the holdings ledger use a single neutral number system. */
.fg-portfolio-value {
  margin: 8px 0 0;
  color: #08080a;
  font: 600 60px/1.1 var(--fg-font);
  letter-spacing: -0.055em;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}
.fg-table-wrap {
  width: 100%;
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-inline: contain;
}
.fg-table {
  width: 100%;
  border: 0;
  border-collapse: collapse;
  background: var(--fg-paper);
  color: var(--fg-ink);
  font: 400 16px/1.5 var(--fg-font);
  font-variant-numeric: tabular-nums;
}
.fg-table th {
  padding: 12px 8px;
  border: 0;
  border-bottom: 1px solid #dedee5;
  background: transparent;
  color: var(--fg-muted);
  font-size: 14px;
  font-weight: 400;
  text-transform: none;
  letter-spacing: normal;
  white-space: nowrap;
}
.fg-table td {
  padding: 20px 8px;
  border: 0;
  border-bottom: 1px solid var(--fg-rule);
  background: transparent;
  vertical-align: baseline;
}
.fg-table th:first-child,
.fg-table td:first-child { padding-left: 0; text-align: left; }
.fg-table th:last-child,
.fg-table td:last-child { padding-right: 0; }
.fg-table th:not(:first-child),
.fg-table td:not(:first-child) { text-align: right; }
.fg-table tfoot td {
  padding-top: 24px;
  border-bottom: 0;
  font-weight: 500;
}
.fg-table--key-value td {
  padding-top: 14px;
  padding-bottom: 14px;
}
.fg-table--key-value td:first-child {
  width: 43%;
  color: var(--fg-secondary);
}
.fg-table--key-value td:not(:first-child) { text-align: left; }
.fg-table--key-value tr:last-child td { border-bottom: 0; }
[data-testid="stMain"] [data-testid="stMetricValue"] {
  color: var(--fg-ink);
  font-family: var(--fg-font);
  font-size: 32px;
  font-weight: 400;
  letter-spacing: -0.035em;
  font-variant-numeric: tabular-nums;
}
[data-testid="stMain"] [data-testid="stMetricLabel"] p {
  color: var(--fg-secondary);
  font-size: 15px;
}

@media (max-width: 1100px) {
  [data-testid="stMainBlockContainer"] { padding: 64px 32px 40px; }
  .fg-page-title { font-size: 34px; }
  .fg-proposal-action { font-size: 68px; }
  .fg-portfolio-value { font-size: 46px; }
}
@media (max-width: 900px) {
  [data-testid="stMainBlockContainer"] { padding: 64px 24px 32px; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 0 !important;
  }
  .st-key-analysis_toolbar [data-testid="stHorizontalBlock"] {
    display: grid;
    grid-template-columns: minmax(110px, 1fr) minmax(140px, 1.25fr) auto;
    align-items: end;
    gap: 10px;
  }
  .st-key-analysis_toolbar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    width: auto !important;
    min-width: 0 !important;
  }
  .st-key-page_header { margin-bottom: 20px; }
  .fg-page-title { font-size: 32px; }
  .fg-portfolio-value { font-size: 46px; }
}
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] { padding: 64px 20px 28px; }
  .fg-page-title { font-size: 29px; }
  .fg-subtitle { font-size: 16px; }
  .fg-proposal-action { font-size: 64px; }
  .fg-inline-facts { font-size: 18px; }
  .fg-rationale { font-size: 16px; }
  .fg-portfolio-value { font-size: 42px; }
  .fg-price { font-size: 26px; }
  .st-key-approval_panel { padding: 20px; border-radius: 16px; }
  .st-key-analysis_toolbar [data-testid="stHorizontalBlock"] {
    grid-template-columns: minmax(90px, 1fr) minmax(125px, 1.2fr) auto;
    gap: 8px;
  }
  .st-key-analysis_toolbar [data-testid="stButton"] button {
    padding-right: 10px;
    padding-left: 10px;
    font-size: 14px;
  }
  .fg-table:not(.fg-table--key-value) { min-width: 580px; }
  .fg-table td { padding-top: 16px; padding-bottom: 16px; }
  [data-testid="stMain"] [data-testid="stMarkdownContainer"] h2:not([class]) { font-size: 24px; }
}
@media (prefers-reduced-motion: reduce) {
  [data-testid="stMain"] button,
  [data-testid="stSidebar"] button { transition: none; }
}
/* Integrated native components and the open definition-list layout. */
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 {
  font-family: var(--fg-font);
  color: var(--fg-ink);
  letter-spacing: -0.035em;
}
[data-testid="stMain"] h1 { font-size: 40px; font-weight: 650; line-height: 1.2; }
[data-testid="stMain"] h2 { font-size: 26px; font-weight: 600; }
[data-testid="stMain"] h3 { font-size: 20px; font-weight: 600; }
[data-testid="stMain"] button p,
[data-testid="stSidebar"] button p { font-family: var(--fg-font); }
.fg-inline-facts { flex-direction: row; align-items: center; gap: 24px; }
.fg-review-summary { font: 600 21px/1.4 var(--fg-font); letter-spacing: -0.02em; }
.fg-key-values { width: 100%; margin: 0; font: 400 16px/1.5 var(--fg-font); }
.fg-key-values > div {
  display: grid; grid-template-columns: minmax(140px, 43%) minmax(0, 1fr);
  padding: 16px 0; gap: 24px; border-bottom: 1px solid var(--fg-rule);
}
.fg-key-values > div:last-child { border-bottom: 0; }
.fg-key-values dt { color: var(--fg-secondary); font-weight: 400; }
.fg-key-values dd { margin: 0; color: var(--fg-ink); overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.st-key-account_details { margin-top: 64px; }
.st-key-current_review { padding: 24px; border-radius: 18px; background: var(--fg-panel); }
.st-key-portfolio_metrics { margin-top: 24px; margin-bottom: 12px; }
.fg-portfolio-value { font-size: 36px; font-weight: 400; overflow-wrap: normal; }
.fg-portfolio-value.is-lead { font-size: 48px; font-weight: 600; }
.st-key-agent_reports { margin-top: 44px; }
.st-key-updated_portfolio { margin-top: 48px; }
.st-key-approval_panel [data-testid="stExpander"] details { background: transparent; }
.st-key-approval_panel [data-testid="stAlert"] {
  padding: 8px 0; border: 0; background: transparent; color: var(--fg-secondary);
}
.st-key-approval_panel [data-testid="stAlert"] p { font-size: 13px; }
@media (max-width: 1100px) {
  .fg-portfolio-value { font-size: 30px; }
  .fg-portfolio-value.is-lead { font-size: 38px; }
}
@media (max-width: 900px) {
  [data-testid="stMain"] h1 { font-size: 34px; }
  .fg-portfolio-value { font-size: 34px; }
  .fg-portfolio-value.is-lead { font-size: 42px; }
  .st-key-account_details { margin-top: 40px; }
}
@media (max-width: 640px) {
  [data-testid="stMain"] h1 { font-size: 30px; }
  .fg-key-values > div { grid-template-columns: minmax(100px, 42%) minmax(0, 1fr); gap: 12px; }
  .fg-inline-facts { gap: 20px; }
  .st-key-agent_reports { margin-top: 32px; }
}

/* Streamlit's sidebar has an extra content gutter; keep our grid in control. */
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebarHeader"] { height: 28px; min-height: 28px; margin-bottom: 0; padding: 0 14px; }
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] { min-height: calc(100dvh - 64px); }
.st-key-sidebar_status { margin-left: 12px; margin-right: 12px; }

[data-testid="stSidebarUserContent"] [data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_status) { margin-top: auto; }
.st-key-sidebar_status { margin: 0; padding: 20px 12px 0; }
.st-key-navigation button > div { justify-content: flex-start; }
.st-key-approval_panel { gap: 10px; }
.st-key-approval_panel h2 { margin: 0; padding: 0; }
.st-key-approval_panel [data-testid="stCaptionContainer"] p { margin: 0; }
.st-key-approval_panel [data-testid="stAlertContainer"] {
  background: transparent; border: 0; padding: 0; color: var(--fg-secondary);
}
.st-key-approval_panel [data-testid="stAlertContentWarning"] { background: transparent; }
.st-key-approval_panel [data-testid="stAlert"] { padding: 0; }
.st-key-approval_panel [data-testid="stExpander"] summary { min-height: 32px; }

"""

# Kept as an alias for simple callers that already refer to a STYLES constant.
STYLES = DASHBOARD_CSS
