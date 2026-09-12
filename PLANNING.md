# Planning Document - AI Sales Intelligence Platform

## Use Cases & Rationale

### Primary Use Case: Cybersecurity Sales Prospecting
**Target User**: Sales teams at cybersecurity software companies
**Core Problem**: Out of thousands of businesses in the market, which ones actually need cybersecurity services right now — and how do we reach them first?

### Selected Use Cases

#### 1. **Opportunity Scoring & Prioritization**
**Why**: Sales teams need to prioritize accounts based on actual need, not guesswork. Traditional prospecting relies on firmographics (industry, company size) which don't indicate immediate security needs.

**Implementation**: Rule-based scoring combining:
- **ICP Fit** (30%): Technical indicators of target company size/complexity
- **Exposure Signals** (20%): Open databases, remote access, attack surface
- **Vulnerability Severity** (20%): Critical CVEs, EOL software
- **Technology Match** (20%): Relevant security technologies detected
- **Recency** (10%): Freshness of intelligence

**Rationale**: Deterministic scoring ensures consistency and explainability. Sales teams can trust the scores and understand why an account ranks high.

#### 2. **Evidence-Based Account Audits**
**Why**: Salespeople need context before outreach. "Why should I call this company?" requires understanding their specific security posture, not just a score.

**Implementation**: AI-generated prospect audits that:
- Explain the precomputed opportunity score
- List observed risks with specific signal names (CVEs, exposed ports)
- Separate observed facts from hypotheses
- Suggest sales next steps tied to evidence

**Rationale**: AI excels at synthesizing technical evidence into business context. Rules handle the scoring; AI handles the explanation.

#### 3. **Natural Language Account Discovery**
**Why**: Sales reps think in questions, not filter combinations. "Show me companies with exposed databases" is more intuitive than setting 5 different filters.

**Implementation**: Hybrid approach:
- **Keyword search**: Fast rules-based filtering for known signal types
- **AI ranking**: Intelligent analysis of the shortlist
- **Fallback**: Keyword matches if AI unavailable

**Rationale**: Pure AI search is expensive and slow. Pure keyword search lacks nuance. Hybrid gives speed + intelligence.

#### 4. **Meeting Preparation Briefs**
**Why**: Sales calls require preparation. Understanding a prospect's security posture helps tailor the pitch.

**Implementation**: AI-generated meeting briefs with:
- Objective for the call
- Evidence-backed talking points
- Discovery questions tied to specific signals

**Rationale**: AI can synthesize account evidence into actionable talking points better than static templates.

#### 5. **Outreach Draft Generation**
**Why**: Personalized outreach converts better. Generic emails get ignored.

**Implementation**: AI-generated email drafts that:
- Cite only observed signals (no invented firmographics)
- Follow evidence, not assumptions
- Keep to 80-120 word optimal length

**Rationale**: AI can personalize at scale while maintaining accuracy through strict evidence constraints.

## Data-Driven Signal Selection

### Hidden Signals in the Dataset
Beyond obvious vulnerability counts, the platform leverages:

1. **Technology Stack Complexity**: Companies with multiple security technologies are more likely to buy additional tools
2. **Cloud Maturity Patterns**: Cloud-native companies have different security needs than on-premises
3. **Geographic Distribution**: Multi-country presence indicates enterprise-scale needs
4. **Attack Surface Evolution**: Changes in exposed services over time indicate security maturity level
5. **Service Port Patterns**: Specific port combinations reveal infrastructure choices

### Signal-to-Use Case Mapping
- **Critical CVEs** → Urgent outreach, audit prioritization
- **Exposed Databases** → Data security product pitch
- **Remote Access (RDP/SSH)** → Access control solutions
- **EOL Software** → Migration/upgrade services
- **Cloud Observations** → Cloud security offerings

## User Experience Design

### Sales Workflow Integration
1. **Morning Pipeline Review**: Radar view of top opportunities by score
2. **Account Deep-Dive**: Select account → AI audit → Understand specific risks
3. **Preparation**: Meeting prep → Talking points tied to signals
4. **Outreach**: Generate personalized email based on evidence
5. **Follow-up**: Save account → Track status in sales workspace

### Filter Hierarchy
1. **Quick Filters**: Search domains, countries, signal types
2. **Score Ranges**: Opportunity score slider for threshold-based prioritization
3. **AI Questions**: Natural language queries for complex discovery
4. **Saved Accounts**: Shortlist for active pipeline management

## Competitive Analysis vs Traditional Tools

### Traditional SDR Tools
- **Firmographic Focus**: Industry, company size, funding
- **Manual Research**: LinkedIn scraping, news monitoring
- **Generic Outreach**: Template-based email sequences
- **Blind Prospecting**: No indication of actual security need

### SignalDesk Advantage
- **Technical Intelligence**: Actual security posture, not company descriptions
- **Evidence-Based**: Every recommendation tied to observed signals
- **AI-Personalized**: Outreach tailored to specific security findings
- **Need-Based**: Prioritizes companies showing security problems, not just big companies

## Success Metrics & Validation

### Product Success Indicators
- **Conversion Rate**: Accounts contacted → Opportunities created
- **Deal Velocity**: Time from first contact to qualified opportunity
- **Outreach Response Rate**: Personalized vs generic email performance
- **User Adoption**: Daily active users, features used per session

### AI Quality Metrics
- **Audit Accuracy**: Precision/recall on evidence inclusion (measured via evals)
- **Hallucination Rate**: Must-not-mention constraint violations
- **Cost Efficiency**: Cost per account processed
- **Latency**: Time from request to AI response

## Go-to-Market Considerations

### Initial Target Segment
- **Mid-Market Security Companies**: 50-500 employees, outbound sales teams
- **Technical Buyers**: Security analysts, CISOs, IT directors
- **Geographic Focus**: North America & Europe (where dataset coverage is strongest)

### Pricing Strategy
- **Freemium**: Basic filtering + limited AI generations
- **Pro Tier**: Unlimited AI + advanced analytics + CRM integration
- **Enterprise**: Custom scoring models + dedicated support + SLAs

### Integration Roadmap
- **Phase 1**: Standalone web app (current implementation)
- **Phase 2**: Salesforce/HubSpot CRM integration
- **Phase 3**: Chrome extension for LinkedIn research
- **Phase 4**: API for custom scoring models

## Risk Mitigation

### Technical Risks
- **AI Quality**: Eval-driven prompt iteration, fallback to keyword search
- **Cost Overrun**: Token monitoring, cheaper models for classification
- **Data Freshness**: Automated data pipelines, recency scoring

### Business Risks
- **Market Fit**: User interviews, rapid prototyping of use cases
- **Competition**: Focus on technical depth vs broad firmographic tools
- **Data Privacy**: Anonymized signals, GDPR compliance, no PII

## Future Enhancement Opportunities

### Near-Term (3-6 months)
- **Custom ICP Models**: User-defined scoring weights
- **Competitor Intelligence**: Track competitor technologies in target accounts
- **Intent Signals**: Website changes, job postings, security incidents

### Long-Term (6-12 months)
- **Predictive Scoring**: ML models for likelihood to buy
- **Automated Outreach Sequences**: Multi-touch campaigns based on signals
- **Team Collaboration**: Shared workspaces, territory assignment

## Conclusion

This platform addresses a real pain point in cybersecurity sales: identifying companies that actually need security solutions based on technical evidence rather than guesswork. The hybrid rule+AI approach balances accuracy, cost, and user experience while providing production-grade AI engineering practices.
