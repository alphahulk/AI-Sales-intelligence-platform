"""Streamlit MVP for cybersecurity opportunity discovery."""

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import streamlit as st
from dotenv import load_dotenv

from src.normalization.technologies import NON_TECHNOLOGY_FIELDS
from src.sales.store import STATUSES, list_accounts, remove_account, save_account, update_account
from src.storage.b2 import ensure_mart
from src.ui.theme import apply_theme, chips, score_ring
from src.workflows.audit import run_prospect_audit
from src.workflows.explore import run_explore
from src.workflows.meeting import run_meeting_prep
from src.workflows.outreach import run_outreach_draft

ROOT = Path(__file__).resolve().parent
MARTS = ROOT / "data" / "marts"

load_dotenv(ROOT / ".env")
SALES_DB = ROOT / "data" / "sales_workspace.db"

st.set_page_config(page_title="SignalDesk", page_icon="S", layout="wide")
apply_theme()


@st.cache_data(show_spinner=False)
def load_accounts() -> list[dict]:
    path = ensure_mart("scored_accounts.parquet", MARTS / "scored_accounts.parquet")
    if not path.exists():
        return []
    connection = duckdb.connect()
    try:
        result = connection.execute(f"SELECT * FROM read_parquet('{path}') ORDER BY opportunity_score DESC, domain")
        columns = [item[0] for item in connection.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        connection.close()


@st.cache_data(show_spinner=False)
def load_signals(domain: str) -> list[dict]:
    path = ensure_mart("account_signals.parquet", MARTS / "account_signals.parquet")
    if not path.exists():
        return []
    connection = duckdb.connect()
    try:
        result = connection.execute(
            f"SELECT signal_type, signal_name, severity, value, confidence, description FROM read_parquet('{path}') WHERE domain = ? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 ELSE 3 END",
            [domain],
        )
        columns = [item[0] for item in connection.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    finally:
        connection.close()


def value(account: dict, key: str, default: object = 0) -> object:
    return account.get(key, default)


def clean_technologies(values: list[str] | None) -> list[str]:
    return [item for item in (values or []) if item not in NON_TECHNOLOGY_FIELDS and not item.startswith("_")]


def metric(label: str, value_: object) -> None:
    st.metric(label, "-" if value_ is None else str(value_))


def primary_country(account: dict) -> str:
    countries = [str(item) for item in (account.get("countries") or []) if item]
    return countries[0] if countries else "—"


def signal_summary(account: dict) -> str:
    tags = []
    if account.get("critical_vulnerability_observations"):
        tags.append("Critical")
    if account.get("exposed_database_count"):
        tags.append("Exposed DB")
    if account.get("exposed_remote_access_count"):
        tags.append("Remote")
    if account.get("eol_observation_count"):
        tags.append("EOL")
    return " · ".join(tags) if tags else "—"


def format_last_seen(raw: object) -> str:
    if not raw:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - parsed).days)
        if days == 0:
            return "today"
        if days == 1:
            return "1 day ago"
        if days < 90:
            return f"{days} days ago"
    except ValueError:
        pass
    return str(raw)[:19]


def filters(accounts: list[dict]) -> tuple[list[dict], int]:
    with st.sidebar:
        st.markdown("# SignalDesk")
        st.caption("Technical cybersecurity prospecting")
        st.divider()
        search = st.text_input("Search domains", placeholder="google, cloud, example")
        counts = Counter(str(country) for account in accounts for country in (account.get("countries") or []) if country)
        countries = st.multiselect("Countries", [item for item, _ in counts.most_common(30)])
        signals = st.multiselect("Signals", ["Critical vulnerability", "Exposed database", "Remote access", "EOL product"])
        cloud_only = st.checkbox("Cloud-observed accounts")
        score_range = st.slider("Opportunity score", 0.0, 100.0, (40.0, 100.0))
        minimum_vulnerabilities = st.number_input("Minimum vulnerabilities", min_value=0, value=0, step=1)
        visible_limit = st.slider("Radar rows", 10, 200, 50, 10)

    matches = []
    for account in accounts:
        domain = str(account.get("domain", ""))
        if search.strip().casefold() not in domain.casefold():
            continue
        if not score_range[0] <= (account.get("opportunity_score") or 0) <= score_range[1]:
            continue
        if countries and not set(countries).intersection(str(item) for item in (account.get("countries") or [])):
            continue
        if cloud_only and not (account.get("cloud_observation_count") or 0):
            continue
        if (account.get("vulnerability_count") or 0) < minimum_vulnerabilities:
            continue
        checks = {
            "Critical vulnerability": (account.get("critical_vulnerability_observations") or 0) > 0,
            "Exposed database": (account.get("exposed_database_count") or 0) > 0,
            "Remote access": (account.get("exposed_remote_access_count") or 0) > 0,
            "EOL product": (account.get("eol_observation_count") or 0) > 0,
        }
        if signals and not all(checks[item] for item in signals):
            continue
        matches.append(account)
    with st.sidebar:
        st.divider()
        st.caption(f"Total accounts · {len(accounts):,}")
        st.caption(f"Matching · {len(matches):,}")
    return matches, visible_limit


def render_analytics(account: dict, signals: list[dict]) -> None:
    score = float(value(account, "opportunity_score", 0) or 0)
    countries = primary_country(account)
    techs = clean_technologies(account.get("technologies"))
    signal_count = len(signals)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown(f"### Account analytics · {account['domain']}")
    st.caption("Domain-level candidate. Network organization is not proof of customer identity.")
    st.markdown(score_ring(score), unsafe_allow_html=True)
    st.markdown(
        "<div class='meta-grid'>"
        f"<div><span>Domain</span><br><b>{account['domain']}</b></div>"
        f"<div><span>Country</span><br><b>{countries}</b></div>"
        f"<div><span>Cloud observed</span><br><b>{'Yes' if account.get('cloud_observation_count') else 'No'}</b></div>"
        f"<div><span>Last seen</span><br><b>{format_last_seen(account.get('last_seen'))}</b></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    stats = st.columns(4)
    for column, label, key in zip(
        stats,
        ("Vulnerabilities", "Signals", "Technologies", "IPs"),
        ("vulnerability_count", None, None, "unique_ip_count"),
    ):
        with column:
            if label == "Signals":
                metric(label, signal_count)
            elif label == "Technologies":
                metric(label, len(techs))
            else:
                metric(label, value(account, key))
    st.markdown("#### Key signals")
    if signals:
        st.dataframe(
            [
                {
                    "Type": item.get("signal_type"),
                    "Name": item.get("signal_name"),
                    "Severity": item.get("severity"),
                    "Confidence": item.get("confidence"),
                }
                for item in signals[:12]
            ],
            width="stretch",
            hide_index=True,
        )
    else:
        st.caption("No named signals for this domain.")
    st.markdown("#### Technologies")
    st.markdown(chips(techs), unsafe_allow_html=True)
    reasons = account.get("score_reasons") or "[]"
    parsed = json.loads(reasons) if isinstance(reasons, str) else reasons
    if parsed:
        st.markdown("#### Score reasons")
        for reason in parsed:
            st.caption(f"• {reason}")
    with st.expander("Write audit, meeting brief, or outreach"):
        render_ai(account, signals, f"panel_{account['domain']}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_signal_summary(accounts: list[dict], selected: dict | None = None) -> None:
    del selected
    if not accounts:
        return
    counts = {
        "Matching accounts": len(accounts),
        "Critical signals": sum((item.get("critical_vulnerability_observations") or 0) > 0 for item in accounts),
        "Cloud observed": sum(1 for item in accounts if item.get("cloud_observation_count")),
        "Avg. opportunity score": sum(item.get("opportunity_score", 0) for item in accounts) / len(accounts),
    }
    st.markdown("#### Quick stats")
    for column, (label, count) in zip(st.columns(4), counts.items()):
        with column:
            metric(label, f"{count:,.1f}" if isinstance(count, float) else f"{count:,}")


def render_radar(accounts: list[dict], limit: int) -> str | None:
    st.caption("Click a row to open account analytics on the right.")
    if not accounts:
        st.info("No accounts match the current filters.")
        return None
    visible = accounts[:limit]
    rows = [
        {
            "Domain": item["domain"],
            "Country": primary_country(item),
            "Opportunity": round(item["opportunity_score"], 1),
            "Vulnerabilities": item.get("vulnerability_count", 0),
            "Signals": signal_summary(item),
            "Cloud": "Yes" if item.get("cloud_observation_count") else "",
        }
        for item in visible
    ]
    selection = st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        height=460,
        on_select="rerun",
        selection_mode="single-row",
        key="opportunity_table",
        column_config={
            "Opportunity": st.column_config.ProgressColumn("Opportunity", min_value=0, max_value=100, format="%.1f"),
            "Vulnerabilities": st.column_config.NumberColumn("Vulnerabilities", format="%d"),
        },
    )
    if not selection.selection.rows:
        return None
    selected_domain = visible[selection.selection.rows[0]]["domain"]
    saved_domains = {item["domain"] for item in list_accounts(SALES_DB)}
    if selected_domain in saved_domains:
        st.success(f"Saved: {selected_domain}")
        if st.button("Remove from saved accounts", key=f"remove_{selected_domain}"):
            remove_account(SALES_DB, selected_domain)
            st.rerun()
    elif st.button("Save selected account", key=f"save_{selected_domain}"):
        save_account(SALES_DB, selected_domain)
        st.rerun()
    return selected_domain


def render_generation(result) -> None:
    if result.error:
        st.error(result.error)
        return
    cached = "cached" if result.cached else f"{result.latency_ms} ms"
    st.caption(
        f"{result.model} · {result.prompt_version} · {cached} · "
        f"{result.input_tokens}+{result.output_tokens} tokens · ${result.cost_usd:.6f}"
    )
    st.markdown(result.text)


def render_ai(account: dict, signals: list[dict], view: str = "radar") -> None:
    st.caption("Optional drafts for this domain. Scores stay deterministic.")
    # Use session-based counter to ensure unique keys across renders
    if "widget_counter" not in st.session_state:
        st.session_state.widget_counter = 0
    st.session_state.widget_counter += 1
    widget_key = f"{view}_{st.session_state.widget_counter}"
    action = st.segmented_control(
        "Workflow",
        ["Prospect audit", "Meeting preparation", "Outreach draft"],
        default="Prospect audit",
        key=f"ai_workflow_{widget_key}",
    )
    st.write(f"{account['domain']} has an opportunity score of {account['opportunity_score']:.1f}.")
    st.write("Signals:", [signal["signal_name"] for signal in signals[:12]])
    if action == "Prospect audit":
        state_key = f"audit_{widget_key}"
        if st.button("Generate prospect audit", key=f"generate_audit_{widget_key}"):
            with st.spinner("Calling AI provider with account evidence..."):
                st.session_state[state_key] = run_prospect_audit(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])
    elif action == "Meeting preparation":
        state_key = f"meeting_{widget_key}"
        if st.button("Generate meeting brief", key=f"generate_meeting_{widget_key}"):
            with st.spinner("Calling AI provider with account evidence..."):
                st.session_state[state_key] = run_meeting_prep(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])
    else:
        state_key = f"outreach_{widget_key}"
        if st.button("Generate outreach draft", key=f"generate_outreach_{widget_key}"):
            with st.spinner("Calling AI provider with account evidence..."):
                st.session_state[state_key] = run_outreach_draft(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])


def render_ask(matches: list[dict]) -> None:
    st.markdown(
        '<div class="ask-banner"><h2>✨ Ask SignalDesk AI</h2>'
        "<p>Ask questions about accounts, vulnerabilities, technologies and opportunity signals</p></div>",
        unsafe_allow_html=True,
    )
    with st.form("ask_signaldesk"):
        question = st.text_input(
            "Question",
            value=st.session_state.get("ask_question", ""),
            placeholder="Which accounts have exposed databases or critical CVEs?",
            label_visibility="collapsed",
        )
        ask, clear = st.columns([1, 1])
        with ask:
            submitted = st.form_submit_button("Ask", width="stretch")
        with clear:
            cleared = st.form_submit_button("Clear", width="stretch")
    if cleared:
        for key in ("ask_question", "ask_explanation", "ask_domains", "ask_error"):
            st.session_state.pop(key, None)
        st.rerun()
    if submitted:
        if not question.strip():
            st.warning("Enter a question, or use the table below as usual.")
        else:
            with st.spinner("Searching accounts, then asking AI provider to explain..."):
                result = run_explore(question.strip(), matches)
            st.session_state["ask_question"] = question.strip()
            st.session_state["ask_explanation"] = result.explanation
            st.session_state["ask_domains"] = result.domains
            st.session_state["ask_error"] = result.error
            st.rerun()
    if st.session_state.get("ask_question"):
        st.caption(f"Question · {st.session_state['ask_question']}")
        if st.session_state.get("ask_error"):
            st.error(st.session_state["ask_error"])
            st.caption("Showing keyword matches until AI provider is available.")
        if st.session_state.get("ask_explanation"):
            st.info(st.session_state["ask_explanation"])


def apply_ask(matches: list[dict]) -> list[dict]:
    domains = st.session_state.get("ask_domains") or []
    if not domains:
        return matches
    by_domain = {item["domain"]: item for item in matches}
    ordered = [by_domain[domain] for domain in domains if domain in by_domain]
    return ordered or matches


def main() -> None:
    accounts = load_accounts()
    if not accounts:
        st.error("Scored account mart not found. Run scripts/build_scores.py first.")
        return
    matches, limit = filters(accounts)
    radar_tab, saved_tab = st.tabs(["Top opportunities", "Saved accounts"])
    with radar_tab:
        render_ask(matches)
        visible = apply_ask(matches)
        st.markdown('<p class="hero-title">Top opportunities</p>', unsafe_allow_html=True)
        if st.session_state.get("ask_question"):
            st.markdown(
                f'<p class="hero-sub">Accounts matching your question, then sidebar filters. Showing {min(limit, len(visible)):,} of {len(visible):,}.</p>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<p class="hero-sub">Accounts ranked by opportunity score with applied filters. Showing {min(limit, len(visible)):,} of {len(matches):,}.</p>',
                unsafe_allow_html=True,
            )
        selected = render_radar(visible, limit)
        render_signal_summary(visible, None)
        selected_account = next((item for item in accounts if item["domain"] == selected), None) if selected else None
        if selected_account:
            render_analytics(selected_account, load_signals(selected))
        elif not visible:
            st.info("No account matches the current filters.")
        else:
            st.markdown(
                '<div class="empty-panel">Select a domain in the table to open account analytics.</div>',
                unsafe_allow_html=True,
            )

    with saved_tab:
        saved_records = list_accounts(SALES_DB)
        saved_by_domain = {item["domain"]: item for item in saved_records}
        saved = [account for account in accounts if account["domain"] in saved_by_domain]
        st.markdown('<p class="hero-title">Saved accounts</p>', unsafe_allow_html=True)
        st.caption("Your shortlist for follow-up, audit, meeting preparation, and outreach.")
        if not saved:
            st.info("No saved accounts yet. Select a row in Top opportunities and choose Save selected account.")
        else:
            saved_rows = [{
                "Domain": account["domain"],
                "Opportunity": round(account["opportunity_score"], 1),
                "Status": saved_by_domain[account["domain"]]["status"],
                "Owner": saved_by_domain[account["domain"]]["owner"],
                "Critical": account.get("critical_vulnerability_observations", 0),
                "Databases": account.get("exposed_database_count", 0),
                "Last observed": str(account.get("last_seen", ""))[:19],
            } for account in saved]
            saved_selection = st.dataframe(saved_rows, width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key="saved_accounts_table")
            if saved_selection.selection.rows:
                selected = saved[saved_selection.selection.rows[0]]
                selected_signals = load_signals(selected["domain"])
                saved_record = saved_by_domain[selected["domain"]]
                with st.expander("Sales qualification", expanded=True):
                    form_key = selected["domain"].replace(".", "_")
                    with st.form(f"qualification_{form_key}"):
                        owner = st.text_input("Owner", value=saved_record["owner"])
                        status = st.selectbox("Status", STATUSES, index=STATUSES.index(saved_record["status"]))
                        next_action = st.text_input("Next action", value=saved_record["next_action"])
                        next_action_date = st.text_input("Next action date", value=saved_record["next_action_date"], placeholder="YYYY-MM-DD")
                        notes = st.text_area("Sales notes", value=saved_record["notes"])
                        submitted = st.form_submit_button("Save qualification")
                    if submitted:
                        update_account(SALES_DB, selected["domain"], owner, status, notes, next_action, next_action_date)
                        st.success("Sales qualification saved.")
                render_analytics(selected, selected_signals)


if __name__ == "__main__":
    main()
