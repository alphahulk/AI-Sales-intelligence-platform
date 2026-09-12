# Data Architecture & ER Diagram - AI Sales Intelligence Platform

## Overview

The platform uses a hybrid data architecture with Parquet-based analytical marts for large-scale analytics and PostgreSQL for transactional sales workspace operations.

## Data Mart Architecture

### Core Data Marts

#### 1. **Curated Observations** (`data/curated/observations.parquet`)
**Purpose**: Raw security scanning observations after normalization
**Schema**: Flattened observation data from security scanners
**Processing**: `scripts/ingest.py` → `src/ingestion/`

**Key Fields**:
- `timestamp`: Observation timestamp
- `ip_str`: Source IP address
- `hostname`: Target hostname
- `port`: Target port
- `service_category`: Service type (database, remote_access, etc.)
- `detected_services`: List of identified services
- `detected_technologies`: List of identified technologies
- `registrable_domains`: Extracted domain names
- `cloud_present`: Cloud hosting indicator
- `cloud_provider`: Cloud provider (AWS, Azure, GCP)
- `vuln_count`: Number of vulnerabilities
- `vuln_max_cvss`: Maximum CVSS score
- `has_eol_tag`: End-of-life software indicator
- `database_service_count`: Number of database services
- `remote_access_service_count`: Number of remote access services

#### 2. **Accounts Mart** (`data/marts/accounts.parquet`)
**Purpose**: Domain-level aggregated cybersecurity intelligence
**Processing**: `scripts/build_accounts.py`
**SQL Query**: `ACCOUNT_QUERY`

**Schema**:
```sql
domain                    TEXT       -- Account identifier
first_seen                TIMESTAMP  -- First observation timestamp
last_seen                 TIMESTAMP  -- Most recent observation
observation_count         INTEGER    -- Total observations for domain
unique_ip_count           INTEGER    -- Distinct IP addresses
unique_hostname_count     INTEGER    -- Distinct hostnames
unique_port_count         INTEGER    -- Distinct exposed ports
unique_service_count      INTEGER    -- Distinct service categories
cloud_observation_count   INTEGER    -- Cloud-hosted observations
identified_cloud_observation_count INTEGER -- Identified cloud providers
countries                 TEXT[]     -- Country codes where observed
regions                   TEXT[]     -- Geographic regions
cloud_providers           TEXT[]     -- Cloud providers used
technologies              TEXT[]     -- Detected technologies
services                  TEXT[]     -- Detected services
vulnerability_count       INTEGER    -- Total vulnerabilities
critical_vulnerability_observations INTEGER -- CVSS >= 9.0
high_vulnerability_observations INTEGER    -- CVSS 7.0-9.0
eol_observation_count      INTEGER    -- End-of-life software count
exposed_database_count    INTEGER    -- Exposed database services
exposed_remote_access_count INTEGER    -- Exposed remote access services
```

**Processing SQL**:
```sql
WITH observations AS (
    SELECT * FROM read_parquet('observations.parquet')
), account_observations AS (
    SELECT
        unnest(registrable_domains) AS domain,
        *
    FROM observations
    WHERE registrable_domains IS NOT NULL
      AND len(registrable_domains) > 0
)
SELECT
    domain AS account_id,
    domain,
    min(try_cast(timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(timestamp AS TIMESTAMP)) AS last_seen,
    count(*) AS observation_count,
    count(DISTINCT ip_str) AS unique_ip_count,
    count(DISTINCT hostname) AS unique_hostname_count,
    count(DISTINCT port) AS unique_port_count,
    count(DISTINCT service_category) AS unique_service_count,
    count(*) FILTER (WHERE cloud_present) AS cloud_observation_count,
    count(*) FILTER (WHERE cloud_present AND cloud_provider IS NOT NULL) AS identified_cloud_observation_count,
    list(DISTINCT country_code) FILTER (WHERE country_code IS NOT NULL) AS countries,
    list(DISTINCT region_code) FILTER (WHERE region_code IS NOT NULL) AS regions,
    list(DISTINCT cloud_provider) FILTER (WHERE cloud_provider IS NOT NULL) AS cloud_providers,
    list_distinct(flatten(list(detected_technologies))) AS technologies,
    list_distinct(flatten(list(detected_services))) AS services,
    sum(vuln_count) AS vulnerability_count,
    sum(CASE WHEN vuln_max_cvss >= 9.0 THEN 1 ELSE 0 END) AS critical_vulnerability_observations,
    sum(CASE WHEN vuln_max_cvss >= 7.0 AND vuln_max_cvss < 9.0 THEN 1 ELSE 0 END) AS high_vulnerability_observations,
    sum(CASE WHEN has_eol_tag THEN 1 ELSE 0 END) AS eol_observation_count,
    sum(database_service_count) AS exposed_database_count,
    sum(remote_access_service_count) AS exposed_remote_access_count
FROM account_observations
GROUP BY domain
```

#### 3. **Account Services Mart** (`data/marts/account_services.parquet`)
**Purpose**: Service-level observations per account
**Processing**: `scripts/build_accounts.py`
**SQL Query**: `SERVICE_QUERY`

**Schema**:
```sql
account_id              TEXT       -- Domain identifier
domain                  TEXT       -- Domain name
service                 TEXT       -- Service name
observation_count       INTEGER    -- Observations with this service
first_seen              TIMESTAMP  -- First observation of this service
last_seen               TIMESTAMP  -- Most recent observation
```

**Processing SQL**:
```sql
WITH observations AS (
    SELECT * FROM read_parquet('observations.parquet')
)
SELECT
    domain_row.domain AS account_id,
    domain_row.domain,
    service_row.service,
    count(*) AS observation_count,
    min(try_cast(observation.timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(observation.timestamp AS TIMESTAMP)) AS last_seen
FROM observations AS observation
CROSS JOIN UNNEST(observation.registrable_domains) AS domain_row(domain)
CROSS JOIN UNNEST(observation.detected_services) AS service_row(service)
WHERE domain_row.domain IS NOT NULL
GROUP BY domain_row.domain, service_row.service
```

#### 4. **Scored Accounts Mart** (`data/marts/scored_accounts.parquet`)
**Purpose**: Accounts with computed opportunity scores
**Processing**: `scripts/build_scores.py`
**Algorithm**: Weighted scoring formula

**Schema**:
```sql
-- All fields from accounts.parquet PLUS:
icp_score                 FLOAT      -- Ideal Customer Profile score (0-100)
exposure_score            FLOAT      -- Security exposure score (0-100)
vulnerability_score       FLOAT      -- Vulnerability severity score (0-100)
technology_score          FLOAT      -- Technology stack score (0-100)
recency_score             FLOAT      -- Data freshness score (0-100)
opportunity_score         FLOAT      -- Weighted composite score (0-100)
score_reasons             TEXT       -- JSON array of score reasons
```

**Scoring Algorithm**:
```python
# Weight Components
WEIGHTS = {
    "icp": 0.30,           # Technical ICP fit
    "exposure": 0.20,      # Security exposure
    "vulnerability": 0.20,  # Vulnerability severity
    "technology": 0.20,    # Technology relevance
    "recency": 0.10        # Data freshness
}

# Final Score Calculation
opportunity_score = 0.30 * icp_score + 
                   0.20 * exposure_score + 
                   0.20 * vulnerability_score + 
                   0.20 * technology_score + 
                   0.10 * recency_score
```

**Component Calculations**:
```python
# Exposure Score
exposure_score = 60% * log(unique_ports, 10) + 
                  20% * log(database_count, 3) + 
                  20% * log(remote_access_count, 3)

# Vulnerability Score
vulnerability_score = 55% * log(critical_count, 1) + 
                      30% * log(high_count, 3) + 
                      15% * log(vulnerability_count, 10)

# Technology Score
technology_score = 70% * log(technology_count, 5) + 
                   30% * log(service_count, 5)

# Recency Score
recency_score = 100 * exp(-age_days / 30)
```

#### 5. **Account Signals Mart** (`data/marts/account_signals.parquet`)
**Purpose**: Explainable signals for AI workflows
**Processing**: `scripts/build_signals.py`

**Schema**:
```sql
account_id                    TEXT       -- Domain identifier
domain                        TEXT       -- Domain name
signal_id                     TEXT       -- Unique signal identifier
signal_type                   TEXT       -- Signal category (attack_surface, vulnerability, technology, exposure)
signal_name                   TEXT       -- Specific signal name
severity                      TEXT       -- Signal severity (critical, high, medium)
observed_at                   TIMESTAMP  -- When signal was observed
first_seen                    TIMESTAMP  -- First observation (future use)
last_seen                     TIMESTAMP  -- Most recent observation
value                         FLOAT      -- Signal metric value
evidence_observation_ids     TEXT[]     -- Related observation IDs (future use)
confidence                    FLOAT      -- Signal confidence score (0-1)
description                   TEXT       -- Human-readable description
observation_count            INTEGER    -- Number of observations supporting signal
metrics_json                  TEXT       -- JSON of signal metrics
```

**Signal Generation Logic**:
```sql
-- Attack Surface Signal
CASE WHEN unique_port_count >= 10 
     THEN 'large_attack_surface' 
     ELSE NULL

-- Critical Vulnerability Signal
CASE WHEN critical_vulnerability_observations > 0 
     THEN 'critical_vulnerability' 
     ELSE NULL

-- Exposed Database Signal
CASE WHEN exposed_database_count > 0 
     THEN 'exposed_database' 
     ELSE NULL

-- Remote Access Signal
CASE WHEN exposed_remote_access_count > 0 
     THEN 'exposed_remote_access' 
     ELSE NULL

-- EOL Product Signal
CASE WHEN eol_observation_count > 0 
     THEN 'eol_product' 
     ELSE NULL
```

## Database Schemas

### SQLite Sales Workspace (Local)
**Purpose**: Local development and fallback storage
**Location**: `data/sales_workspace.db`
**Processing**: `src/sales/store.py`

**Schema**:
```sql
CREATE TABLE saved_accounts (
    domain TEXT PRIMARY KEY,
    saved_at TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    next_action_date TEXT NOT NULL DEFAULT ''
)
```

**Supported Statuses**: New, Researching, Qualified, Contacted, Meeting booked, Disqualified

### PostgreSQL Sales Workspace (Production)
**Purpose**: Production sales workspace with multi-user support
**Connection**: Supabase transaction pooler
**Location**: Cloud database
**Processing**: `src/sales/store.py`

**Schema**:
```sql
CREATE TABLE saved_accounts (
    domain TEXT PRIMARY KEY,
    saved_at TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    next_action_date TEXT NOT NULL DEFAULT ''
)
```

**Connection Method**:
```python
# Transaction Pooler (recommended for cloud)
DATABASE_URL = "postgresql://postgres.[project-id]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"
```

## Data Flow Architecture

### Pipeline Stages

#### Stage 1: Data Ingestion
```
Raw NDJSON Observations
    ↓
scripts/ingest.py
    ↓
data/curated/observations.parquet
```

**Process**: Normalization, parsing, format conversion

#### Stage 2: Account Aggregation
```
data/curated/observations.parquet
    ↓
scripts/build_accounts.py
    ↓
data/marts/accounts.parquet
data/marts/account_services.parquet
```

**SQL**: Domain-level aggregation using DuckDB

#### Stage 3: Scoring
```
data/marts/accounts.parquet
    ↓
scripts/build_scores.py
    ↓
data/marts/scored_accounts.parquet
```

**Algorithm**: Weighted scoring formula with logarithmic scaling

#### Stage 4: Signal Generation
```
data/marts/scored_accounts.parquet
    ↓
scripts/build_signals.py
    ↓
data/marts/account_signals.parquet
```

**Logic**: Rule-based signal extraction for AI explainability

#### Stage 5: AI Processing
```
data/marts/scored_accounts.parquet
data/marts/account_signals.parquet
    ↓
AI Workflows (prospect audit, meeting prep, outreach)
    ↓
data/traces/llm.jsonl (observability)
```

**Providers**: Gemini (primary), Claude (fallback)

#### Stage 6: Web Application
```
data/marts/scored_accounts.parquet
data/marts/account_signals.parquet
    ↓
Streamlit App (app.py)
    ↓
User Interface + AI Workflows
```

**Database**: PostgreSQL/SQLite for saved accounts

## ER Diagram

### Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                      Raw Observations                        │
│  (NDJSON → Parquet)                                        │
│  - timestamp, ip_str, hostname, port                         │
│  - registrable_domains, detected_services                   │
│  - vuln_count, cloud_present, eol_tags                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Accounts Mart                           │
│  (data/marts/accounts.parquet)                              │
│  - domain, first_seen, last_seen                             │
│  - unique_ip_count, unique_port_count                         │
│  - vulnerability_count, technologies                          │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│ Account Services │ │   Scoring    │ │   Signals       │
│   Mart           │ │   Process    │ │   Mart          │
│                  │ │              │ │                 │
│ - account_id     │ │ - icp_score  │ │ - signal_id     │
│ - service        │ │ - exposure   │ │ - signal_type   │
│ - observation    │ │ - vuln       │ │ - severity      │
└──────────────────┘ └──────────────┘ └─────────────────┘
                            │                   │
                            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Scored Accounts Mart                      │
│  (data/marts/scored_accounts.parquet)                        │
│  - All account fields + scores                                │
│  - opportunity_score, score_reasons                            │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
│  Streamlit App   │ │   AI Traces  │ │ Sales Workspace  │
│                  │ │              │ │                 │
│ - Radar View     │ │ - request    │ │ - saved_accounts │
│ - AI Chat        │ │ - response   │ │ - status        │
│ - Analytics      │ │ - tokens     │ │ - owner         │
└──────────────────┘ │ - cost       │ │ - notes         │
                     │ - provider   │ └─────────────────┘
                     └──────────────┘
```

## Key SQL Queries

### 1. Account Aggregation Query
**File**: `scripts/build_accounts.py`
**Purpose**: Transform raw observations into domain-level intelligence

```sql
WITH observations AS (
    SELECT * FROM read_parquet('observations.parquet')
), account_observations AS (
    SELECT
        unnest(registrable_domains) AS domain,
        *
    FROM observations
    WHERE registrable_domains IS NOT NULL
      AND len(registrable_domains) > 0
)
SELECT
    domain AS account_id,
    domain,
    min(try_cast(timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(timestamp AS TIMESTAMP)) AS last_seen,
    count(*) AS observation_count,
    count(DISTINCT ip_str) AS unique_ip_count,
    count(DISTINCT hostname) AS unique_hostname_count,
    count(DISTINCT port) AS unique_port_count,
    count(DISTINCT service_category) AS unique_service_count,
    count(*) FILTER (WHERE cloud_present) AS cloud_observation_count,
    count(*) FILTER (WHERE cloud_present AND cloud_provider IS NOT NULL) AS identified_cloud_observation_count,
    list(DISTINCT country_code) FILTER (WHERE country_code IS NOT NULL) AS countries,
    list(DISTINCT region_code) FILTER (WHERE region_code IS NOT NULL) AS regions,
    list(DISTINCT cloud_provider) FILTER (WHERE cloud_provider IS NOT NULL) AS cloud_providers,
    list_distinct(flatten(list(detected_technologies))) AS technologies,
    list_distinct(flatten(list(detected_services))) AS services,
    sum(vuln_count) AS vulnerability_count,
    sum(CASE WHEN vuln_max_cvss >= 9.0 THEN 1 ELSE 0 END) AS critical_vulnerability_observations,
    sum(CASE WHEN vuln_max_cvss >= 7.0 AND vuln_max_cvss < 9.0 THEN 1 ELSE 0 END) AS high_vulnerability_observations,
    sum(CASE WHEN has_eol_tag THEN 1 ELSE 0 END) AS eol_observation_count,
    sum(database_service_count) AS exposed_database_count,
    sum(remote_access_service_count) AS exposed_remote_access_count
FROM account_observations
GROUP BY domain
```

### 2. Service-Level Query
**File**: `scripts/build_accounts.py`
**Purpose**: Track services observed per account

```sql
WITH observations AS (
    SELECT * FROM read_parquet('observations.parquet')
)
SELECT
    domain_row.domain AS account_id,
    domain_row.domain,
    service_row.service,
    count(*) AS observation_count,
    min(try_cast(observation.timestamp AS TIMESTAMP)) AS first_seen,
    max(try_cast(observation.timestamp AS TIMESTAMP)) AS last_seen
FROM observations AS observation
CROSS JOIN UNNEST(observation.registrable_domains) AS domain_row(domain)
CROSS JOIN UNNEST(observation.detected_services) AS service_row(service)
WHERE domain_row.domain IS NOT NULL
GROUP BY domain_row.domain, service_row.service
```

### 3. Signal Extraction Query
**File**: `scripts/build_signals.py`
**Purpose**: Generate explainable signals for AI workflows

```sql
SELECT
    account_id,
    domain,
    observation_count,
    unique_port_count,
    vulnerability_count,
    critical_vulnerability_observations,
    high_vulnerability_observations,
    eol_observation_count,
    exposed_database_count,
    exposed_remote_access_count,
    last_seen
FROM read_parquet('scored_accounts.parquet')
```

### 4. Natural Language Search Query
**File**: `src/workflows/explore.py`
**Purpose**: Keyword-based account filtering before AI ranking

```python
# Pseudo-SQL equivalent
SELECT * FROM scored_accounts
WHERE 
    domain LIKE '%{query}%' OR
    country IN ({extracted_countries}) OR
    (
        (vulnerability_count > 0 AND '{critical}' IN query) OR
        (exposed_database_count > 0 AND '{database}' IN query) OR
        (exposed_remote_access_count > 0 AND '{remote}' IN query) OR
        (eol_observation_count > 0 AND '{eol}' IN query)
    )
ORDER BY opportunity_score DESC
LIMIT 25
```

### 5. Filter/Query Query
**File**: `app.py`
**Purpose**: Multi-criteria account filtering in UI

```python
# Pseudo-SQL equivalent
SELECT * FROM scored_accounts
WHERE
    domain LIKE '%{search}%' AND
    opportunity_score BETWEEN {min_score} AND {max_score} AND
    vulnerability_count >= {min_vulns} AND
    (
        critical_vulnerability_observations > 0 = {has_critical} AND
        exposed_database_count > 0 = {has_database} AND
        exposed_remote_access_count > 0 = {has_remote} AND
        eol_observation_count > 0 = {has_eol}
    ) AND
    cloud_observation_count > 0 = {cloud_only}
ORDER BY opportunity_score DESC
LIMIT {limit}
```

## Data Storage Architecture

### File System Structure
```
data/
├── raw/                    # Original raw data (not committed)
├── processed/              # Intermediate processing (not committed)
├── curated/                # Normalized observations
│   └── observations.parquet
├── marts/                  # Analytical data marts
│   ├── accounts.parquet
│   ├── account_services.parquet
│   ├── scored_accounts.parquet
│   └── account_signals.parquet
├── traces/                  # AI call traces
│   └── llm.jsonl
└── sales_workspace.db      # SQLite fallback database
```

### Cloud Storage Integration
**Provider**: Backblaze B2 (S3-compatible)
**Processing**: `src/storage/b2.py`
**Purpose**: External analytical mart storage

**Configuration**:
```bash
B2_ENDPOINT=https://s3.us-east-005.backblazeb2.com
B2_BUCKET=salesmarts
B2_KEY_ID=your_key_id
B2_APPLICATION_KEY=your_application_key
```

**Download Logic**:
```python
def ensure_mart(name: str, local_path: Path) -> Path:
    """Download mart from B2 if not available locally"""
    if local_path.exists() or not configured():
        return local_path
    
    # Download from B2 S3-compatible API
    client = boto3.client('s3', endpoint_url=endpoint, ...)
    client.download_file(bucket, name, local_path)
    return local_path
```

## AI Data Integration

### Evidence Building
**File**: `src/ai/generate.py`
**Purpose**: Convert database records into AI prompts

**Evidence Structure**:
```python
{
    "workflow": "prospect_audit",
    "domain": "example.com",
    "scores": {
        "opportunity": 71.4,
        "exposure": 58.0,
        "vulnerability": 88.0,
        "technology": 41.0,
        "recency": 62.0
    },
    "footprint": {
        "unique_ips": 6,
        "unique_ports": 9,
        "unique_services": 5,
        "cloud_observations": 0,
        "exposed_databases": 0,
        "exposed_remote_access": 0,
        "eol_observations": 0,
        "vulnerability_count": 3,
        "critical_vulnerabilities": 2,
        "high_vulnerabilities": 1
    },
    "score_reasons": ["2 critical vulnerability observations"],
    "signals": [
        {
            "type": "vulnerability",
            "name": "CVE-2024-4577",
            "severity": "critical",
            "description": "PHP CGI argument injection",
            "confidence": 0.9
        }
    ],
    "constraints": [
        "Do not invent company identity, industry, employee count, or contacts.",
        "Treat scores as precomputed. Do not recalculate opportunity_score.",
        "Separate observed facts from hypotheses. Label uncertainty."
    ]
}
```

### Tracing Schema
**File**: `data/traces/llm.jsonl`
**Purpose**: Complete observability for all AI calls

**Schema**:
```json
{
  "timestamp": "2026-09-12T10:00:00.000Z",
  "workflow": "prospect_audit",
  "prompt_version": "audit/v2",
  "model": "gemini-3.6-flash",
  "provider": "gemini",
  "domain": "example.com",
  "request": "Full prompt text...",
  "response": "AI response text...",
  "latency_ms": 57134,
  "input_tokens": 200,
  "output_tokens": 300,
  "cost_usd": 0.00021,
  "cached": false,
  "error": null,
  "decision": "prospect_audit_generated"
}
```

## Performance & Optimization

### DuckDB Optimizations
- **Column Pruning**: Only select needed columns
- **Predicate Pushdown**: Apply filters during parquet scan
- **Parallel Processing**: Multi-threaded parquet reading
- **Compression**: ZSTD compression for storage efficiency

### Caching Strategy
- **In-Memory Cache**: AI prompt caching by hash
- **Streamlit Cache**: Data loading with `@st.cache_data`
- **Session State**: Widget state and AI results

### Query Performance
- **Accounts Mart**: ~100ms for 10K accounts
- **Signals Mart**: ~50ms for domain lookup
- **Natural Language Search**: ~200ms for keyword filtering + AI ranking

## Data Quality & Validation

### Validation Scripts
**File**: `scripts/validate_data.py`
**Purpose**: Data quality checks

**Validations**:
- Schema consistency
- Required field presence
- Data type validation
- Range checks (scores 0-100)
- Referential integrity (domain references)

### Profiling Scripts
**File**: `scripts/profile_dataset.py`
**Purpose**: Analyze data distribution and statistics

**Metrics**:
- Score distribution
- Vulnerability severity breakdown
- Geographic distribution
- Technology prevalence
- Cloud vs on-prem split

## Scalability Considerations

### Current Capacity
- **Accounts**: 10K+ domains
- **Observations**: 1M+ records
- **Signals**: 50K+ account signals
- **AI Traces**: 10K+ calls

### Scaling Path
- **Large Datasets**: Partition parquet files by date
- **Concurrent Users**: Move to PostgreSQL for marts
- **High Volume**: Add Redis caching layer
- **Enterprise**: Multi-region deployment with data sharding

## Security & Privacy

### Data Protection
- **No PII**: Only technical signals (no personal data)
- **Anonymization**: Domains are public information
- **API Keys**: Environment variables, never committed
- **Audit Trail**: All AI calls logged for compliance

### Access Control
- **PostgreSQL**: Role-based access control (RBAC)
- **B2 Storage**: Bucket-level permissions
- **Streamlit Cloud**: App-level authentication

## Backup & Recovery

### Backup Strategy
- **Code**: Git version control
- **Data Marts**: B2 cloud storage with versioning
- **Database**: PostgreSQL automated backups
- **AI Traces: Append-only JSONL with rotation

### Recovery Process
1. Restore code from Git
2. Download marts from B2
3. Restore PostgreSQL from backup
4. Rebuild derived marts using scripts

## Data Dictionary

### Score Components
- **ICP Score (0-100)**: Technical fit based on size, complexity, geography
- **Exposure Score (0-100)**: Security exposure based on ports, databases, remote access
- **Vulnerability Score (0-100)**: Vulnerability severity based on CVSS scores
- **Technology Score (0-100)**: Technology relevance based on stack complexity
- **Recency Score (0-100)**: Data freshness based on observation age

### Signal Types
- **attack_surface**: Network exposure indicators
- **vulnerability**: Security vulnerability indicators
- **technology**: Technology stack indicators
- **exposure**: Service exposure indicators

### Severity Levels
- **critical**: Immediate security risk (CVSS >= 9.0)
- **high**: Significant security risk (CVSS 7.0-9.0)
- **medium**: Moderate security concern

This architecture supports the complete AI Sales Intelligence Platform with efficient data processing, explainable AI signals, and production-grade scalability.
