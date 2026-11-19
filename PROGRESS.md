# ScholarSetu — Engineering Progress & Milestone Tracker

*Candidate:* Durgesh Rajendra Shewale (CSE, S.No. 3, Roll 2124UCEM2042)  
*Repository:* [DurgeshShewale29/Cream-AI](https://github.com/DurgeshShewale29/Cream-AI)  
*Status:* **All 14 Days Complete (100% Closed)**  

---

## 📋 Comprehensive Day-by-Day Milestone Log

### Day 1: Project Genesis & Scoping
- [x] Define product scope: ScholarSetu for Maharashtra engineering students.
- [x] Create project card with user personas, problem statement, and primary data sources.
- [x] Implement initial interactive CLI menu in `day01_intro.py` and `day01_menu.py`.

### Day 2: Initial Dataset & Exploration
- [x] Hand-collect 20 foundational schemes in `data/sample_records.py` (10 DTE Maharashtra + 10 Central NSP).
- [x] Build keyword search and category aggregations in `day02_search.py`.
- [x] Implement core reusable query modules in `app/records.py` (`load_records`, `search`, `count_by`, `get_by_id`).
- [x] Create modular CLI interface in `app/cli.py`.

### Day 3: Automated Ingestion & Data Modeling
- [x] Build robust HTML scraper in `app/fetch.py` with retries, timeouts, and error recovery for DTE Maharashtra and NSP portals.
- [x] Implement HTML parser in `app/ingest.py` extracting scheme attributes into clean JSON.
- [x] Define typed `Record` dataclass in `app/models.py`.
- [x] Normalize records and output validated `data/records.json`.

### Day 4: Backend Microservice & TF-IDF Search
- [x] Build production FastAPI backend in `app/main.py`.
- [x] Implement `GET /health` reporting service status and loaded record count.
- [x] Implement `GET /records` and `GET /records/{id}` with 404 validation.
- [x] Build sparse search engine in `app/smart_search.py` using TF-IDF and cosine similarity.
- [x] Implement `GET /search?q=` with score ranking.
- [x] Implement `POST /questions` logging student questions to `data/questions.json`.
- [x] Conduct exploratory data analysis in `analysis/explore.py` using Pandas.

### Day 5: LLM Foundations & Technical Documentation
- [x] Draft comprehensive technical guide `docs/how_llms_work.md` covering tokenization, attention, and inference mechanics.
- [x] Create visual architecture diagram illustrating transformer operations.
- [x] Formulate 10 representative student questions, including unanswerable out-of-domain query (Q6).

### Day 6: Unified LLM Client & Prompt Benchmarking
- [x] Implement provider-agnostic LLM interface in `app/llm.py` supporting Groq (Llama 3.3 70B) and Google Gemini (2.5 Flash).
- [x] Build `POST /chat` with JSON schema enforcement and confidence classification.
- [x] Design prompt versions in `prompts/system.txt`, `prompts/task_v1.txt`, and `prompts/task_v2.txt`.
- [x] Run prompt benchmark across test set and generate comparison report in `eval/prompt_compare.md`.

### Day 7: Semantic Embeddings & Persistent Vectorstore
- [x] Implement document chunking in `app/chunking.py` preserving metadata (source URL, title, page).
- [x] Build dense vector search in `app/embed.py` using `sentence-transformers/all-MiniLM-L6-v2`.
- [x] Establish persistent ChromaDB index in `data/chroma/` via `app/vectorstore.py`.
- [x] Implement `GET /search/semantic` endpoint for dense vector retrieval.

### Day 8: Grounded RAG & Automated Evaluation Harness
- [x] Build citation-grounded RAG pipeline in `app/rag.py` enforcing `[n]` source citations.
- [x] Implement strict refusal logic (*"I don't know"*) for unanswerable queries.
- [x] Implement `POST /ask` endpoint returning answers, citations, and confidence.
- [x] Construct 15-question ground-truth evaluation set in `eval/eval_set.json`.
- [x] Build evaluation benchmark in `eval/run_eval.py` comparing Config A (120 words) vs Config B (60 words).
- [x] Select Config B as winning configuration (100% retrieval hit-rate, 14/15 accuracy) and publish `eval/eval_results.md`.

### Day 9: Autonomous Agent Loop & LangGraph State Graph
- [x] Build comparative analysis tool `app/tools.py` producing Markdown comparison tables.
- [x] Implement autonomous Reason-Act-Observe loop in `app/agent_loop.py`.
- [x] Rebuild agent using LangGraph in `app/graph.py` with stateful conversation memory.
- [x] Implement Human-in-the-Loop approval gate pausing execution before running comparison tools.
- [x] Expose `POST /agent` supporting turn initiation, approval pause, and resume.

### Day 10: Streamlit UI & Signature Stacking Optimizer
- [x] Develop interactive Streamlit chat interface in `ui/app.py` with multi-turn tabs and citation cards.
- [x] Architect the **Signature Stacking Engine** in `app/stacking.py`:
  - Detect mutual exclusivity between MahaDBT and NSP tuition-fee scholarships.
  - Implement fee-sensitive dynamic preference ranking (calculating exact rupee yield).
  - Enable hostel maintenance allowance stacking (Dr. Panjabrao Deshmukh).
- [x] Implement thumbs up/down feedback persistence via `POST /feedback` and `GET /feedback`.
- [x] Add 15 automated tests in `tests/test_day10.py` covering stacking rules, fee flips, and Streamlit AppTest.

### Day 11: Test Suite Hardening, Ruff Compliance & Docker Compose
- [x] Expand `pytest` suite across records, smart search, RAG, agent loop, and stacking.
- [x] Achieve 100% clean linting across entire repository (`ruff check .` with 0 errors).
- [x] Author cloud-ready `Dockerfile` and `.dockerignore`.
- [x] Construct multi-container `docker-compose.yml` linking FastAPI backend and Streamlit UI with persistent volumes.

### Day 12: Automated CI/CD & Cloud Deployment
- [x] Build GitHub Actions CI workflow in `.github/workflows/ci.yml` (Ruff, pytest, and Docker container smoke test).
- [x] Add green CI status badge to `README.md`.
- [x] Create feature branch `feat/day-12-ci-and-deploy`, pass all CI checks, and merge Pull Request #1 into `main`.
- [x] Deploy live production web service to **Render** with CPU-optimized PyTorch.
- [x] Configure root redirect to interactive Swagger documentation (`/docs`).

### Day 13: Production Hardening, Caching & Selling README
- [x] Implement request latency and token telemetry middleware logging ms and token usage (`X-Process-Time-Ms`, `X-Total-Tokens`).
- [x] Build in-memory thread-safe LRU/TTL query cache in `app/cache.py` with `/cache/stats` and `/cache/clear`.
- [x] Enforce input boundaries (500 chars max, null-byte rejection) and prompt-injection defense in `app/security.py`.
- [x] Add 11 automated security, cache, and telemetry tests in `tests/test_day13.py` (53 total tests passing).
- [x] Document real production benchmark numbers in `README.md` (1,450.9 ms cold vs 0.19 ms warm hit, 7,463x speedup).
- [x] Revamp `README.md` with problem pitch, Mermaid architecture diagram, demo video link, and results tables.
- [x] Author 3 quantifiable, ATS-optimized resume bullet points in `docs/resume.md`.

### Day 14: Interview Preparation, Demo Rehearsals & Final Release
- [x] Author comprehensive interview guide in `docs/interview.md` containing:
  - 60-second spoken pitch.
  - Deep-dive STAR interview story on the hardest engineering problem (multi-condition rule matrix in code vs LLM guessing).
  - 10 senior-level technical and product interview Q&As.
- [x] Close every item in `PROGRESS.md`.
- [x] Execute and verify two complete end-to-end automated demo rehearsals (`docs/demo_rehearsal.md`).
- [x] Create annotated git tag `final` and push to remote repository.

---

## 📊 Summary Scorecard

| Category | Metric | Status |
|---|---|---|
| **Total Automated Tests** | 53 unit, integration & AppTest tests | ✅ 100% Passing |
| **Linting & Code Quality** | `ruff check .` | ✅ 0 Errors |
| **Cloud Deployment** | Render (`https://cream-ai.onrender.com`) | ✅ Live & Healthy |
| **CI/CD Automation** | GitHub Actions Workflow | ✅ Passing & Green |
| **Git Milestones** | `week-1`, `checkpoint-1`, `checkpoint-2`, `checkpoint-3`, `day-13`, `final` | ✅ Tagged & Pushed |
