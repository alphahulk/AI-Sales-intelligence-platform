# AI Sales Intelligence Platform - Knowledge Base

## Scoring System

### Opportunity Score Formula
The opportunity score is a weighted combination of multiple factors, not just vulnerability count:

```python
weights = {"icp": 0.30, "exposure": 0.20, "vulnerability": 0.20, "technology": 0.20, "recency": 0.10}
```

**Final Score = 30% ICP + 20% Exposure + 20% Vulnerability + 20% Technology + 10% Recency**

### Score Components

#### ICP Score (30% weight)
- **Size indicators**: IP count (optimal range: 3-200), service count (≥3), technology count (≥2)
- **Geographic presence**: Multiple countries (+10 points)
- **Cloud maturity**: Cloud observations with specific patterns
- **Base score**: 40 points, with bonuses/penalties based on above factors

#### Exposure Score (20% weight)
- Exposed databases
- Remote access services (RDP, SSH, VNC, etc.)
- Other security exposures

#### Vulnerability Score (20% weight)
- Total vulnerability count
- Critical vulnerabilities
- High/CVSS scores
- EOL (End-of-Life) software instances

#### Technology Score (20% weight)
- Relevant cybersecurity technologies detected
- Technology stack complexity
- Target technology matches

#### Recency Score (10% weight)
- How recently the account was observed
- Freshness of intelligence data

### Why Higher Score ≠ More Vulnerabilities
An account with fewer vulnerabilities but better ICP fit, exposure, and technology match might score higher than one with many vulnerabilities but poor ICP fit. This makes the scoring more business-relevant than just "most vulnerabilities first."

## Multi-Provider AI System

### Architecture
- **Base Provider Interface**: `src/ai/base_provider.py` - Abstract base class for all AI providers
- **Gemini Provider**: `src/ai/gemini_provider.py` - Google Gemini implementation
- **Claude Provider**: `src/ai/claude_provider.py` - Anthropic Claude implementation  
- **Provider Manager**: `src/ai/provider_manager.py` - Handles provider selection and automatic fallback

### Configuration
```bash
# Provider priority (comma-separated)
AI_FALLBACK_ORDER=gemini,claude

# API Keys
GOOGLE_API_KEY=your_gemini_key
CLAUDE_API_KEY=your_claude_key

# Model selection
AI_MODEL=gemini-3.6-flash  # or claude-3-5-haiku-20241022
```

### Fallback Logic
1. Try primary provider (first in `AI_FALLBACK_ORDER`)
2. On failure (timeout, rate limit, error), automatically try next provider
3. Provider-specific error handling and retry logic
4. Timeouts: 120 seconds for both providers

### Smart Model Selection
- If `AI_MODEL` is set to a Gemini model, Claude provider automatically uses its default
- If `AI_MODEL` is set to a Claude model, Gemini provider automatically uses its default
- Default models: `gemini-3.6-flash`, `claude-3-5-haiku-20241022`

### Cost Tracking
- Both Gemini and Claude pricing rates included in `src/ai/tracing.py`
- Provider information tracked in all AI call traces
- Cost estimation works for both providers

## AI Chat & Table Ranking

### Current Flow
1. **User types question** in AI chat box
2. **Keyword search first**: Rules-based search finds up to 25 matching accounts
3. **AI analysis**: Shortlist sent to AI provider for intelligent ranking
4. **Table updates**: Shows AI-ranked results based on question

### When AI Chat is Used
- Table shows: "Accounts matching your question, then sidebar filters"
- Results are: **AI-ranked based on your question**
- Original opportunity scores still visible but not primary sort

### When AI Chat is NOT Used
- Table shows: "Accounts ranked by opportunity score with applied filters"
- Results are: **Original opportunity score ranking**

### Hybrid Approach
- **Rules-based filtering** (keyword search) - fast, deterministic
- **AI ranking** (on shortlist) - intelligent analysis
- **Fallback** - if AI fails, shows keyword matches

## Environment Setup

### Virtual Environment
```bash
# Activate virtual environment
source .venv/Scripts/activate  # Linux/Mac
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Key Dependencies
- `anthropic>=0.18.0` - Claude API SDK
- `streamlit>=1.38` - UI framework
- `duckdb>=1.0` - Database
- Other data processing libraries

## Verification Commands

### Test Provider Configuration
```python
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.') / '.env')
from src.ai.provider import configured, get_available_providers, get_active_provider, model_name
print('Configured:', configured())
print('Available providers:', get_available_providers())
print('Active provider:', get_active_provider())
print('Model:', model_name())
```

### Test Individual Providers
```python
# Test Gemini
from src.ai.gemini_provider import GeminiProvider
gemini = GeminiProvider()
result = gemini.complete("What is 2+2?")
print(result.text)

# Test Claude
from src.ai.claude_provider import ClaudeProvider
claude = ClaudeProvider()
result = claude.complete("What is 2+2?")
print(result.text)
```

## Workflow Files

### AI Workflows
- **Prospect Audit**: `src/workflows/audit.py` - Account analysis and risk assessment
- **Meeting Prep**: `src/workflows/meeting.py` - Meeting brief generation
- **Outreach**: `src/workflows/outreach.py` - Email draft generation
- **Explore**: `src/workflows/explore.py` - Natural language account search

### Prompts
- Located in `prompts/` directory
- Versioned prompts (v1.md, v2.md, etc.)
- Each workflow has its own prompt directory

## Data Flow

### Account Data
1. **Ingestion**: Raw data → Normalized format
2. **Scoring**: Account signals → Opportunity scores
3. **Storage**: Parquet files in `data/marts/`
4. **UI**: Streamlit app loads and displays accounts

### AI Generation
1. **Evidence Building**: Account data + signals → Structured evidence
2. **Prompt Composition**: Instructions + evidence → Final prompt
3. **AI Call**: Provider manager → AI provider → Completion
4. **Result Processing**: Text + metadata → Generation result
5. **Tracing**: All calls logged to `data/traces/llm.jsonl`

## Troubleshooting

### Common Issues

#### Claude Credit Balance Error
```
Your credit balance is too low to access the Anthropic API
```
**Solution**: Add credits at https://console.anthropic.com/

#### Timeout Errors
**Solution**: Increased to 120s timeout in both providers. If still timing out, check network connectivity or API status.

#### Provider Not Configured
**Solution**: Check API keys in `.env` file and ensure they're not empty.

#### Import Errors
**Solution**: Ensure virtual environment is activated and dependencies installed.

## Development Notes

### Adding New Providers
1. Create new provider class inheriting from `BaseProvider`
2. Implement required methods: `complete()`, `configured()`, `model_name()`, `provider_name()`
3. Add pricing rates to `src/ai/tracing.py`
4. Add provider initialization to `src/ai/provider_manager.py`
5. Update `.env.example` with configuration options

### Modifying Scoring Weights
Edit weights in `src/scoring/opportunity.py`:
```python
weights = {"icp": 0.30, "exposure": 0.20, "vulnerability": 0.20, "technology": 0.20, "recency": 0.10}
```
Ensure weights sum to 1.0.

### Adding New Workflows
1. Create workflow file in `src/workflows/`
2. Create prompt file in `prompts/{workflow_name}/`
3. Implement evidence building and prompt composition
4. Add UI integration in `app.py` if needed
