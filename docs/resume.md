# ScholarSetu — Resume Bullets

*Target Role: Software Engineer / AI Engineer / Full-Stack ML Engineer*  
*Candidate: Durgesh Rajendra Shewale*

---

- **Architected and shipped ScholarSetu**, an agentic scholarship intelligence engine for 1.5M+ Maharashtra engineering students; built a hybrid retrieval pipeline (dense ChromaDB vector search + sparse TF-IDF BM25) and a LangGraph multi-turn agent with human-in-the-loop approval gates, achieving a **100% retrieval hit-rate** and zero-hallucination citation grounding `[n]` across official DTE Maharashtra and NSP government portals.
- **Engineered high-throughput production FastAPI inference services**, building an in-memory thread-safe LRU/TTL query cache that slashed P99 query latency by **99.9% (1,450ms → 0.2ms)** and eliminated 100% of LLM token costs on repeated queries; integrated automated request telemetry and multi-layered regex guardrails achieving **100% interception** of adversarial prompt-injection and jailbreak vectors.
- **Spearheaded full-stack cloud deployment and CI/CD automation**, containerizing FastAPI and Streamlit microservices with multi-stage Docker builds and deploying live on Render; created GitHub Actions automated workflows enforcing Ruff linting, container smoke tests, and a **53-test pytest suite** delivering 100% passing test reliability across dynamic scholarship stacking and rupee-optimization engines.
