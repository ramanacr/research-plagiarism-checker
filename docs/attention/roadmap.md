# Research Ingestion & Altmetrics Integration Roadmap

This document maps out the strategy to diversify the digital evidence sources for tracking citation footprints. Based on cost-benefit analysis, we prioritize **Free/Open (Category 1)** and **Freemium (Category 2)** sources for immediate integration, reserving **Paid/Commercial (Category 3)** options as future considerations.

---

## 🗺️ Roadmap Overview

```
                   [Current State: Wikipedia Direct Crawl]
                                     │
                                     ▼
        ┌─────────────────────────────────────────────────────────┐
        │   PHASE 1: Open & Freemium Integrations (Immediate)     │
        │                                                         │
        │   - OpenAlex API (Citation Graphs & Metrics)            │
        │   - Crossref Event Data (Blogs & Science Portals)       │
        │   - PubPeer API (Post-Publication Peer Reviews)         │
        │   - Lens.org API (Free Patent Citations)                │
        │   - GitHub Search API (Software Repo Mentions)          │
        └────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
        ┌─────────────────────────────────────────────────────────┐
        │   PHASE 2: Commercial Aggregators (Future Decision)     │
        │                                                         │
        │   - Altmetric Explorer API                              │
        │   - Overton API (Government & NGO Policy Briefs)        │
        └─────────────────────────────────────────────────────────┘
```

---

## 🚀 Phase 1: Open & Freemium Integrations (Immediate Focus)

These sources require **no subscription costs** and will be integrated into the local background crawler workflow.

### 1. OpenAlex Integration
*   **Purpose**: Tracks bibliographic citations, citation counts, and author collaboration networks.
*   **Implementation**: Query `https://api.openalex.org/works/pmid:{pmid}` or `doi:{doi}`.
*   **Action Plan**: Retrieve references count and cache it in `attention_evidence` logs.

### 2. Crossref Event Data Integration
*   **Purpose**: Captures references to publications across blogs, scientific forums, and news feeds.
*   **Implementation**: Connect to Crossref's open Event Data query endpoints.

### 3. PubPeer Integration
*   **Purpose**: Checks if a publication has active critiques, validation comments, or retraction flags in the post-publication peer-review community.
*   **Implementation**: Query the PubPeer API by DOI. If reviews exist, tag them as active alerts on the client dashboard.

### 4. Patent Linkage via Lens.org
*   **Purpose**: Discovers if the publication has been cited in global patent documents (WIPO, USPTO, EPO).
*   **Implementation**: Use a free developer/non-commercial API key from Lens.org to fetch patent relationships.

### 5. Developer Code Mentions via GitHub
*   **Purpose**: Identifies open-source software libraries that implement or reference the research findings.
*   **Implementation**: Use the GitHub Search Code API with a developer OAuth token to search for literal PMID/DOI strings.

---

## 🔮 Phase 2: Commercial Aggregators (Future Considerations)

These integrations are deferred to future budget decisions when scaling to institutional or enterprise-level deployments.

### 1. Altmetric Explorer API
*   **Trigger Criteria**: Required if the client demands pre-calculated article attention scores ("Altmetric Donut") or real-time social feed tracking (X/Twitter feeds) that cannot be crawled directly.
*   **Cost Barrier**: High institutional subscription.
*   **Workaround**: Display the Altmetric Badge widget in the frontend client dashboard (which is free to display for publishers and libraries).

### 2. Overton Policy tracking
*   **Trigger Criteria**: Required if comprehensive NGO, think tank, and intergovernmental policy citations (WHO, CDC, United Nations) are needed.
*   **Cost Barrier**: High commercial subscription.
