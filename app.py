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
            }], use_container_width=True, hide_index=True)
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


def render_signal_summary(accounts: list[dict]) -> None:
    st.markdown("## Signal bar")
    st.caption("A portfolio-level view of why matched accounts need attention. Select an account in the radar above for details.")
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
    selection = st.dataframe(rows, use_container_width=True, hide_index=True, height=420, on_select="rerun", selection_mode="single-row", key="opportunity_table")
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


def render_ai(account: dict, signals: list[dict], view: str = "radar") -> None:
    st.title("AI workspace")
    st.caption("Use one selected account at a time for evidence-led workflows.")
    widget_key = f"{view}_{str(account['domain']).replace('.', '_')}"
    action = st.segmented_control(
        "Workflow",
        ["Prospect audit", "Meeting preparation", "Outreach draft"],
        default="Prospect audit",
        key=f"ai_workflow_{widget_key}",
    )
    if action == "Prospect audit":
        st.write(f"{account['domain']} has an opportunity score of {account['opportunity_score']:.1f}.")
        st.write("Signals:", [signal["signal_name"] for signal in signals])
    elif action == "Meeting preparation":
        st.text_area("Meeting brief", "Review the observed attack surface, critical vulnerabilities, exposed services, and remediation ownership before the meeting.", height=220, key=f"meeting_brief_{widget_key}")
    else:
        st.text_area("Outreach draft", f"Subject: Internet-facing exposure at {account['domain']}\n\nHi {{first_name}},\n\nWe observed security signals associated with {account['domain']}. Would a short conversation about how you monitor your external attack surface be useful?", height=220, key=f"outreach_draft_{widget_key}")


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
        render_signal_summary(matches)
        if selected:
            account = next(item for item in accounts if item["domain"] == selected)
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
            saved_selection = st.dataframe(saved_rows, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="saved_accounts_table")
            if saved_selection.selection.rows:
                selected = saved[saved_selection.selection.rows[0]]
                selected_signals = load_signals(selected["domain"])
                render_analytics(selected, selected_signals)
                saved_record = saved_by_domain[selected["domain"]]
                with st.expander("Sales qualification", expanded=True):
                    form_key = selected["domain"].replace(".", "_")
                    owner = st.text_input("Owner", value=saved_record["owner"], key=f"owner_{form_key}")
                    status = st.selectbox("Status", STATUSES, index=STATUSES.index(saved_record["status"]), key=f"status_{form_key}")
                    next_action = st.text_input("Next action", value=saved_record["next_action"], key=f"next_action_{form_key}")
                    next_action_date = st.text_input("Next action date", value=saved_record["next_action_date"], placeholder="YYYY-MM-DD", key=f"next_date_{form_key}")
                    notes = st.text_area("Sales notes", value=saved_record["notes"], key=f"notes_{form_key}")
                    if st.button("Save qualification", key=f"save_qualification_{form_key}"):
                        update_account(SALES_DB, selected["domain"], owner, status, notes, next_action, next_action_date)
                        st.success("Sales qualification saved.")
                st.divider()
                render_ai(selected, selected_signals, "saved")


if __name__ == "__main__":
    main()
