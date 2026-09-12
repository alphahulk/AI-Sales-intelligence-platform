# Planning

SignalDesk is a prospecting console for a cybersecurity vendor: given internet-observation data, **which domains look like they need help this week, and what should a seller say first?**

## Use cases we built

### 1. This-week prioritisation (Opportunity radar)

SDRs do not read 372k rows. They filter by score band, country, and buying-adjacent **technical signals** (critical vulns, exposed databases, remote access, EOL). Deterministic `opportunity_score` ranks the queue. This is the core ICP-adjacent motion the dataset actually supports: exposure and exploitability, not firmographic fit.

### 2. Call prep (account analytics + meeting brief)

After a row is selected, the seller needs evidence, not a chatbot. Analytics tabs show footprint, vulns, and score reasons. **Generate meeting brief** turns that pack into discovery questions tied to named signals.

### 3. First outreach (saved accounts + outreach draft)

Sellers shortlist domains, set owner/status/next action in Supabase (or local SQLite), then **Generate outreach draft**. Copy must cite observed signals only — no fake contacts.

## Use cases we did not build

- Full CRM, sequencing, or mailbox send — out of scope for a prototype; qualification fields are the seam.
- Firmographic ICP (industry, headcount, installed security stack as a *buyer* attribute) — **not in the source file**. ICP weight is a neutral `50` and called out in scoring docs.
- Letting an LLM rescore the warehouse — expensive and unauditable; rules already produce `score_reasons`.

## Research → product mapping

| Sales practice | In this app |
|---|---|
| ICP / TAM cut | Score components + filters (geo, cloud-observed, vuln floor) |
| Buying signals | Critical CVE, exposed DB, RDP/SSH, EOL banners |
| Territory | Country multiselect from observed countries |
| Outreach priority | Sort by opportunity score; save for follow-up |
| Personalisation | LLM workflows on **selected** evidence only |

Build order matched that: profile → Parquet observations → account marts → scores → Streamlit → Gemini on the shortlist.
