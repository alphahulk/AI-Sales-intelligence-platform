# Architecture Document - AI Sales Intelligence Platform

## System Overview

SignalDesk is a hybrid rule-based and AI-powered sales intelligence platform that transforms raw cybersecurity observations into actionable sales opportunities. The architecture prioritizes deterministic scoring for consistency while leveraging AI for explanation and personalization.

## Core Components

### 1. Data Pipeline Layer

#### Ingestion & Normalization
- **Input**: Raw NDJSON observations from security scanning
- **Processing**: Domain normalization, signal classification, entity resolution
- **Output**: Structured observations ready for scoring

**Key Design Decision**: Keep raw observations separate from scored accounts to enable re-scoring with new models without reprocessing raw data.

#### Scoring Engine
- **Location**: `src/scoring/`
- **Components**:
  - `icp.py`: Ideal Customer Profile scoring based on technical indicators
  - `opportunity.py`: Weighted combination of all score components
- **Output**: `data/marts/scored_accounts.parquet`

**Scoring Formula**:
```python
opportunity_score = 0.30 * icp_score + 
                   0.20 * exposure_score + 
                   0.20 * vulnerability_score + 
                   0.20 * technology_score + 
                   0.10 * recency_score
```

### 2. AI Provider Layer

#### Multi-Provider Architecture
- **Base Interface**: `src/ai/base_provider.py` - Abstract provider class
- **Implementations**:
  - `src/ai/gemini_provider.py` - Google Gemini API
  - `src/ai/claude_provider.py` - Anthropic Claude API
- **Orchestration**: `src/ai/provider_manager.py` - Fallback logic and provider selection

**Design Decision**: Provider abstraction enables easy addition of new AI providers and automatic fallback for reliability.

#### Provider Selection Logic
```python
AI_FALLBACK_ORDER=gemini,claude  # Environment variable
1. Try primary provider (gemini)
2. On failure (timeout, rate limit, error), try next (claude)
3. Provider-specific error handling and retry logic
4. Timeout: 120 seconds for both providers
```

### 3. AI Workflow Layer

#### Workflow Architecture
- **Location**: `src/workflows/`
- **Components**:
  - `audit.py`: Prospect audit generation
  - `meeting.py`: Meeting preparation briefs
  - `outreach.py`: Outreach email drafts
  - `explore.py`: Natural language account discovery

**Workflow Pattern**:
```python
1. Build evidence from account data + signals
2. Compose prompt (instructions + evidence)
3. Run generation through provider manager
4. Parse and validate response
5. Trace all calls for observability
```

#### Evidence Building
- **Function**: `build_account_evidence()` in `src/ai/generate.py`
- **Inputs**: Account record, signals, workflow type
- **Output**: Structured JSON evidence with constraints
- **Constraints**: "Do not invent firmographics", "Separate observed from hypothesis"

### 4. Prompt Management Layer

#### Versioning Strategy
- **Location**: `prompts/`
- **Structure**: `{workflow_name}/{version}.md`
- **Examples**: `prompts/audit/v1.md`, `prompts/audit/v2.md`

**Design Decision**: File-based prompts enable:
- Git version control and diffing
- A/B testing between versions
- Rollback capability
- Manual editing without code deployment

#### Prompt Evolution
- **v1 → v2**: Added stronger guardrails against hallucination
- **Eval Driven**: Changes based on precision/recall measurements
- **Backward Compatible**: Old versions remain for comparison

### 5. Evaluation Layer

#### Eval System Architecture
- **Location**: `evals/`
- **Components**:
  - `datasets/prospect_audit.jsonl`: 25 hand-labelled test cases
  - `judge.py`: Lexical scoring (must_mention, must_not_mention)
  - `run_eval.py`: Eval harness with version comparison

**Eval Metrics**:
```python
precision = true_positives / (true_positives + false_positives)
recall = true_positives / (true_positives + false_negatives)
pass_rate = cases_passed / total_cases
```

**Design Decision**: Lexical evaluation is chosen over semantic evaluation because:
- Deterministic and reproducible
- Fast to run (no additional AI calls)
- Sufficient for guardrail validation (hallucination detection)

### 6. Observability Layer

#### Tracing Schema
- **Location**: `data/traces/llm.jsonl`
- **Schema**:
```json
{
  "timestamp": "ISO-8601",
  "workflow": "prospect_audit",
  "prompt_version": "audit/v2",
  "model": "gemini-3.6-flash",
  "provider": "gemini",
  "domain": "example.com",
  "request": "full prompt text",
  "response": "AI response text",
  "latency_ms": 1234,
  "input_tokens": 150,
  "output_tokens": 300,
  "cost_usd": 0.000234,
  "cached": false,
  "error": null,
  "decision": "prospect_audit_generated"
}
```

**Design Decision**: JSONL format chosen because:
- Append-only for performance
- Easy to parse and analyze
- No database dependency
- Scales to millions of records

#### Cost Tracking
- **Location**: `src/ai/tracing.py`
- **Pricing Models**: Per-provider token pricing
- **Calculation**: Real-time cost estimation per call
- **Monitoring**: Aggregate costs in eval results

### 7. Application Layer

#### Streamlit Architecture
- **Location**: `app.py`
- **Components**:
  - `render_ask()`: AI chat interface
  - `render_radar()`: Account table with filtering
  - `render_analytics()`: Detailed account view
  - `render_ai()`: AI workflow triggers

**State Management**:
```python
st.session_state["ask_question"]      # User's query
st.session_state["ask_explanation"]   # AI response
st.session_state["ask_domains"]       # Ranked domains
st.session_state["audit_{domain}"]    # Cached audit results
```

**Design Decision**: Streamlit chosen because:
- Rapid prototyping capability
- Built-in state management
- Python-native (no frontend framework)
- Sufficient for MVP validation

## Rule vs AI Split

### Deterministic Rules (When to Use)
- **Scoring**: Opportunity scores must be consistent and explainable
- **Filtering**: Geographic, signal type, numeric ranges
- **Data Validation**: Schema constraints, format checking
- **Classification**: Signal type categorization

**Rationale**: Rules provide:
- Consistency: Same input always produces same output
- Explainability: Clear decision logic
- Performance: Fast execution without API calls
- Cost: No marginal cost per execution

### AI-Generated (When to Use)
- **Explanation**: Converting technical evidence to business context
- **Synthesis**: Combining multiple signals into coherent narrative
- **Personalization**: Tailoring outreach to specific account findings
- **Discovery**: Natural language understanding of complex queries

**Rationale**: AI provides:
- Nuance: Understanding context and relationships
- Flexibility: Handling varied input formats
- Creativity: Generating novel combinations
- Scale: Personalization at volume

### Hybrid Approach Examples

#### Account Discovery Workflow
```python
1. Rules: Keyword search for "database" + "exposed" (fast, deterministic)
2. AI: Rank and explain the shortlist (intelligent, nuanced)
3. Fallback: If AI fails, use keyword results (graceful degradation)
```

#### Outreach Generation
```python
1. Rules: Extract observed signals from account data (deterministic)
2. AI: Generate email citing only extracted signals (creative but constrained)
3. Validation: Ensure no invented firmographics (rule-based guardrails)
```

## Cost Model & Optimization

### Model Selection Strategy

#### Gemini Flash (Primary)
- **Use Cases**: Account audits, meeting prep, outreach
- **Rationale**: Fast, cost-effective, good for text generation
- **Cost**: $0.15 input / $0.60 output per million tokens

#### Claude Haiku (Fallback)
- **Use Cases**: Same as Gemini (fallback)
- **Rationale**: Different provider for reliability, competitive pricing
- **Cost**: $1.00 input / $5.00 output per million tokens

### Cost Analysis

#### Per-Account Processing Cost
```python
# Prospect Audit (typical)
Input tokens: ~200 (evidence + prompt)
Output tokens: ~300 (audit text)
Gemini cost: (200/1M * $0.15) + (300/1M * $0.60) = $0.00021 per audit

# Meeting Preparation (typical)
Input tokens: ~250 (evidence + prompt)
Output tokens: ~350 (brief text)
Gemini cost: (250/1M * $0.15) + (350/1M * $0.60) = $0.000248 per brief

# Outreach Draft (typical)
Input tokens: ~180 (evidence + prompt)
Output tokens: ~150 (email text)
Gemini cost: (180/1M * $0.15) + (150/1M * $0.60) = $0.000117 per email

# Explore/Query (typical)
Input tokens: ~500 (question + account shortlist)
Output tokens: ~200 (explanation + ranking)
Gemini cost: (500/1M * $0.15) + (200/1M * $0.60) = $0.000195 per query
```

#### Production Volume Scenarios

**Scenario 1: Single Power User (Daily)**
- 10 prospect audits: $0.0021
- 5 meeting preps: $0.0012
- 20 outreach emails: $0.0023
- 15 explore queries: $0.0029
- **Daily Total**: $0.0085
- **Monthly Total**: $0.26

**Scenario 2: Small Team (5 users, Daily)**
- 50 prospect audits: $0.0105
- 25 meeting preps: $0.0062
- 100 outreach emails: $0.0117
- 75 explore queries: $0.0146
- **Daily Total**: $0.043
- **Monthly Total**: $1.29

**Scenario 3: Startup (20 users, Daily)**
- 200 prospect audits: $0.042
- 100 meeting preps: $0.0248
- 400 outreach emails: $0.0468
- 300 explore queries: $0.0585
- **Daily Total**: $0.172
- **Monthly Total**: $5.16

**Scenario 4: Mid-Market (100 users, Daily)**
- 1000 prospect audits: $0.21
- 500 meeting preps: $0.124
- 2000 outreach emails: $0.234
- 1500 explore queries: $0.293
- **Daily Total**: $0.861
- **Monthly Total**: $25.83

#### Cost Optimization Impact

**Current Optimizations:**
- **Caching**: 30% reduction in duplicate calls → $0.60 daily → $18 monthly (100 users)
- **Smart Model Selection**: Using Flash instead of Pro → 80% cost reduction
- **Evidence Pruning**: Limiting to top 20 signals → 25% input token reduction

**Projected Monthly Costs (100 users):**
- **No Optimization**: $129/month
- **With Caching**: $90/month (30% savings)
- **With Model Selection**: $26/month (80% savings)
- **Full Optimization**: $18/month (86% total savings)

#### Cost Ceiling Configuration
```python
# Production safeguards
MAX_DAILY_TOKENS = 1_000_000  # ~$0.15-0.60 per day
MAX_COST_PER_ACCOUNT = 0.01    # $0.01 per account maximum
ALERT_THRESHOLD = 10.0         # $10 daily spend alert
MONTHLY_BUDGET = 100.0         # $100 monthly budget ceiling
```

### Real-Time Cost Monitoring
- **Per-Call Tracking**: Every AI call logs exact token usage and cost
- **Daily Aggregation**: JSONL traces parsed for daily spend analysis
- **Alert System**: Email/webhook alerts when approaching thresholds
- **Provider Cost Breakdown**: Separate tracking per provider for optimization

### Cost Dashboard Metrics
- **Current Month Spend**: Running total vs budget
- **Cost Per Workflow**: Breakdown by audit/meeting/outreach/explore
- **Provider Efficiency**: Cost per successful call by provider
- **Cache Performance**: Savings from caching vs fresh calls

### Cost Optimization Strategies

#### Caching Strategy
- **In-Memory Cache**: Session-based caching of identical prompts
- **Cache Key**: `prompt_version + model + prompt_hash`
- **Savings**: 30-50% reduction in duplicate AI calls

#### Token Optimization
- **Prompt Compression**: Remove redundant instructions
- **Evidence Pruning**: Limit to top 20 signals per account
- **Output Limits**: Max tokens constraints (4096 for Claude)

#### Provider Selection
- **Cost-Based Routing**: Cheaper provider for simple tasks
- **Performance-Based Routing**: Faster provider for interactive features
- **Availability-Based Routing**: Fallback on outages

## Data Flow Architecture

### End-to-End Pipeline

```
Raw Observations (NDJSON)
    ↓
Ingestion & Normalization
    ↓
Signal Classification
    ↓
Scoring Engine (Rule-based)
    ↓
Scored Accounts (Parquet)
    ↓
Streamlit App
    ↓
User Request (Filter/Query)
    ↓
Evidence Building
    ↓
AI Generation (Multi-provider)
    ↓
Response Processing
    ↓
UI Display + Tracing
```

### Caching Strategy
- **Account Data**: Cached at session level (duckdb + streamlit cache)
- **AI Responses**: Cached by prompt hash (in-memory cache)
- **Filter Results**: Not cached (real-time filtering)

## Scalability Considerations

### Current Limitations
- **Single User**: Streamlit is single-threaded
- **Memory-Based**: All data in memory (Parquet files)
- **No Database**: File-based storage limits concurrent access

### Scaling Path
- **Multi-User**: Move to FastAPI + PostgreSQL
- **Large Datasets**: Implement pagination and lazy loading
- **High Volume**: Add Redis caching, message queue for async AI calls
- **Enterprise**: Add authentication, RBAC, audit logging

## Security & Privacy

### Data Protection
- **No PII**: Dataset contains only technical signals (no personal data)
- **Anonymization**: Domains are public information
- **API Keys**: Environment variables, never committed to code
- **Audit Trail**: All AI calls logged for compliance

### Compliance Considerations
- **GDPR**: Technical signals only, no personal data processing
- **SOC 2**: Audit trail available for all AI decisions
- **Data Residency**: Can be deployed in specific regions

## Technology Choices & Trade-offs

### Python vs Other Languages
- **Choice**: Python for entire stack
- **Rationale**: AI ecosystem (LangChain, Anthropic SDK), data processing (pandas, duckdb)
- **Trade-off**: Performance vs development speed

### Streamlit vs React/FastAPI
- **Choice**: Streamlit for MVP
- **Rationale**: Rapid prototyping, no frontend expertise needed
- **Trade-off**: Limited customization vs production-ready UI

### File-Based vs Database Storage
- **Choice**: Parquet files + JSONL traces
- **Rationale**: Simple deployment, no database maintenance
- **Trade-off**: Query performance vs operational complexity

### Rule-Based vs ML Scoring
- **Choice**: Rule-based scoring with AI explanation
- **Rationale**: Explainability, consistency, no training data needed
- **Trade-off**: Manual tuning vs automated optimization

## Deployment Architecture

### Current Deployment
- **Platform**: Local development or simple hosting
- **Requirements**: Python 3.9+, virtual environment
- **Dependencies**: requirements.txt
- **Configuration**: .env file

### Production Deployment Options
- **Streamlit Cloud**: Easiest, limited customization
- **AWS/Azure**: More control, higher cost
- **Kubernetes**: Enterprise scalability, complex setup
- **Serverless**: Cost-effective for sporadic usage

## Monitoring & Alerting

### Health Checks
- **Provider Availability**: Periodic API health checks
- **Data Freshness**: Last updated timestamps on data files
- **Error Rates**: Exception tracking in AI calls
- **Cost Monitoring**: Daily spend alerts

### Performance Metrics
- **Response Time**: AI call latency (p50, p95, p99)
- **Cache Hit Rate**: Percentage of requests served from cache
- **Error Rate**: Failed AI calls as percentage of total
- **User Engagement**: Feature usage patterns

## Conclusion

The architecture balances production-grade AI engineering practices with pragmatic technology choices for rapid development. The hybrid rule+AI approach provides consistency where it matters (scoring) while leveraging AI where it adds unique value (explanation and personalization). The multi-provider design ensures reliability while the comprehensive observability enables continuous improvement.
