"""Streamlit MVP for cybersecurity opportunity discovery."""

import json
from collections import Counter
from pathlib import Path

import duckdb
import streamlit as st
from dotenv import load_dotenv

from src.normalization.technologies import NON_TECHNOLOGY_FIELDS
from src.sales.store import STATUSES, list_accounts, remove_account, save_account, update_account
from src.storage.b2 import ensure_mart
from src.workflows.audit import run_prospect_audit
from src.workflows.meeting import run_meeting_prep
from src.workflows.outreach import run_outreach_draft

ROOT = Path(__file__).resolve().parent
MARTS = ROOT / "data" / "marts"

load_dotenv(ROOT / ".env")
SALES_DB = ROOT / "data" / "sales_workspace.db"

st.set_page_config(page_title="SignalDesk", page_icon="S", layout="wide")


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
    return matches, visible_limit


def render_analytics(account: dict, signals: list[dict]) -> None:
    st.divider()
    st.title(f"Account analytics · {account['domain']}")
    st.caption("Domain-level candidate. Network organization is not proof of customer identity.")
    score_columns = st.columns(5)
    for column, label in zip(score_columns, ("Opportunity", "Exposure", "Vulnerability", "Technology", "Recency")):
        with column:
            metric(label, round(float(value(account, f"{label.lower()}_score", 0)), 1))
    tabs = st.tabs(["Overview", "Exposure", "Vulnerabilities", "Technology", "Evidence"])
    with tabs[0]:
        left, right = st.columns([1, 1])
        with left:
            st.markdown("#### Footprint")
            st.dataframe([{
                "IPs": value(account, "unique_ip_count"),
                "Ports": value(account, "unique_port_count"),
                "Services": value(account, "unique_service_count"),
                "Cloud observations": value(account, "cloud_observation_count"),
            }], width="stretch", hide_index=True)
        with right:
            chart = {
                "Unique IPs": value(account, "unique_ip_count"),
                "Unique ports": value(account, "unique_port_count"),
                "Vulnerabilities": value(account, "vulnerability_count"),
                "EOL observations": value(account, "eol_observation_count"),
            }
            st.bar_chart(chart, horizontal=True, height=210)
        st.markdown("#### Score reasons")
        reasons = account.get("score_reasons") or "[]"
        st.write(json.loads(reasons) if isinstance(reasons, str) else reasons)
    with tabs[1]:
        cols = st.columns(4)
        for column, label, key in zip(cols, ("Unique ports", "Exposed databases", "Remote access", "EOL observations"), ("unique_port_count", "exposed_database_count", "exposed_remote_access_count", "eol_observation_count")):
            with column:
                metric(label, value(account, key))
        st.write({"services": account.get("services") or [], "cloud_providers": account.get("cloud_providers") or []})
    with tabs[2]:
        cols = st.columns(3)
        for column, label, key in zip(cols, ("Total", "Critical", "High"), ("vulnerability_count", "critical_vulnerability_observations", "high_vulnerability_observations")):
            with column:
                metric(label, value(account, key))
        for signal in signals:
            if signal["signal_type"] == "vulnerability":
                st.error(f"**{signal['severity'].upper()}** · {signal['signal_name']} · {signal['description']}")
    with tabs[3]:
        st.write(clean_technologies(account.get("technologies")))
        st.write({"services": account.get("services") or [], "cloud": account.get("cloud_providers") or []})
    with tabs[4]:
        for signal in signals:
            st.warning(f"**{signal['severity'].upper()}** · {signal['signal_name']} · confidence {signal['confidence']}")


def render_signal_summary(accounts: list[dict], selected: dict | None = None) -> None:
    if selected:
        st.markdown(f"## Signal bar · {selected['domain']}")
        st.caption("Counts for the selected account. Change the radar row to update this bar.")
        counts = {
            "Critical vulnerability": selected.get("critical_vulnerability_observations") or 0,
            "Exposed database": selected.get("exposed_database_count") or 0,
            "Remote access": selected.get("exposed_remote_access_count") or 0,
            "EOL product": selected.get("eol_observation_count") or 0,
        }
    else:
        st.markdown("## Signal bar")
        st.caption("Portfolio view of filtered accounts. Select a radar row to see that account's signal counts.")
        counts = {
            "Critical vulnerability": sum((item.get("critical_vulnerability_observations") or 0) > 0 for item in accounts),
            "Exposed database": sum((item.get("exposed_database_count") or 0) > 0 for item in accounts),
            "Remote access": sum((item.get("exposed_remote_access_count") or 0) > 0 for item in accounts),
            "EOL product": sum((item.get("eol_observation_count") or 0) > 0 for item in accounts),
        }
    for column, (label, count) in zip(st.columns(4), counts.items()):
        with column:
            metric(label, f"{count:,}")
    st.bar_chart(counts, horizontal=True, height=180)


def render_radar(accounts: list[dict], limit: int) -> str | None:
    st.caption("Click a row to open account analytics below.")
    if not accounts:
        st.info("No accounts match the current filters.")
        return None
    summary = st.columns(4)
    for column, label, value_ in zip(summary, ("Accounts", "Critical findings", "Exposed databases", "Average score"), (len(accounts), sum(item.get("critical_vulnerability_observations") or 0 for item in accounts), sum(item.get("exposed_database_count") or 0 for item in accounts), sum(item.get("opportunity_score", 0) for item in accounts) / len(accounts))):
        with column:
            metric(label, f"{value_:,.1f}" if isinstance(value_, float) else f"{value_:,}")
    visible = accounts[:limit]
    rows = [{"Domain": item["domain"], "Opportunity": round(item["opportunity_score"], 1), "Vulnerability": round(item["vulnerability_score"], 1), "Exposure": round(item["exposure_score"], 1), "Critical": item.get("critical_vulnerability_observations", 0), "Databases": item.get("exposed_database_count", 0), "Last observed": str(item.get("last_seen", ""))[:19]} for item in visible]
    selection = st.dataframe(rows, width="stretch", hide_index=True, height=420, on_select="rerun", selection_mode="single-row", key="opportunity_table")
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
    st.title("AI workspace")
    st.caption("Each workflow calls Gemini with this account's scores and signals. Opportunity score stays deterministic.")
    widget_key = f"{view}_{str(account['domain']).replace('.', '_')}"
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
            with st.spinner("Calling Gemini with account evidence..."):
                st.session_state[state_key] = run_prospect_audit(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])
    elif action == "Meeting preparation":
        state_key = f"meeting_{widget_key}"
        if st.button("Generate meeting brief", key=f"generate_meeting_{widget_key}"):
            with st.spinner("Calling Gemini with account evidence..."):
                st.session_state[state_key] = run_meeting_prep(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])
    else:
        state_key = f"outreach_{widget_key}"
        if st.button("Generate outreach draft", key=f"generate_outreach_{widget_key}"):
            with st.spinner("Calling Gemini with account evidence..."):
                st.session_state[state_key] = run_outreach_draft(account, signals)
        if state_key in st.session_state:
            render_generation(st.session_state[state_key])


def main() -> None:
    accounts = load_accounts()
    if not accounts:
        st.error("Scored account mart not found. Run scripts/build_scores.py first.")
        return
    matches, limit = filters(accounts)
    radar_tab, saved_tab = st.tabs(["Opportunity radar", "Saved accounts"])
    with radar_tab:
        st.markdown("# Opportunity radar")
        selected = render_radar(matches, limit)
        selected_account = next((item for item in accounts if item["domain"] == selected), None) if selected else None
        render_signal_summary(matches, selected_account)
        if selected_account:
            account = selected_account
            signals = load_signals(selected)
            render_analytics(account, signals)
            st.divider()
            render_ai(account, signals, "radar")
        elif not matches:
            st.info("No account matches the current filters.")

    with saved_tab:
        saved_records = list_accounts(SALES_DB)
        saved_by_domain = {item["domain"]: item for item in saved_records}
        saved = [account for account in accounts if account["domain"] in saved_by_domain]
        st.markdown("# Saved accounts")
        st.caption("Your shortlist for follow-up, audit, meeting preparation, and outreach.")
        if not saved:
            st.info("No saved accounts yet. Select a row in Opportunity radar and choose Save selected account.")
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
                render_analytics(selected, selected_signals)
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
                st.divider()
                render_ai(selected, selected_signals, "saved")


if __name__ == "__main__":
    main()
