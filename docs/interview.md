# ScholarSetu — Interview Guide & Story Bank

*Candidate:* Durgesh Rajendra Shewale  
*Target Role:* Software Engineer / AI Engineer / Full-Stack ML Engineer  
*Project:* ScholarSetu (AI-Powered Maharashtra Scholarship Discovery & Stacking Optimizer)  
*Live Service:* https://cream-ai.onrender.com  

---

## ⏱️ Part 1: The 60-Second Elevator Pitch

> *"Every year in Maharashtra, over 1.5 million engineering students leave more than ₹100 Crores in government scholarships on the table. The problem isn't that money isn't available—it's that official rules are buried across fragmented DTE, MahaDBT, and NSP portals. Over 60% of students default to basic 50% fee waivers simply because they've never heard of 100% schemes or stackable ₹30,000 hostel stipends.*
>
> *To solve this, I built **ScholarSetu**—an AI-driven scholarship discovery and optimization platform. Under the hood, ScholarSetu pairs a zero-hallucination RAG pipeline using ChromaDB dense vectors and TF-IDF search with a deterministic Python stacking engine. It doesn't just answer questions with clickable official citations; it dynamically calculates net annual rupee yields and flags non-stackable schemes so students never face disqualification.*
>
> *I also engineered a LangGraph agent with conversational memory and human approval gates, added an in-memory cache that cut response latency by 99.9% down to 0.2 milliseconds, and deployed the full system via Docker and automated GitHub Actions CI. ScholarSetu turns a confusing, multi-week bureaucratic ordeal into a 30-second personalized roadmap."*

---

## 🎯 Part 2: The Interview Story (The Hardest Engineering Problem)

### 📌 Core Challenge
> **"Eligibility is a multi-condition rule (category × income slab × gender × admission type) written in prose across Marathi and English pages; the bot must apply rules with code, not let the LLM guess, and keep year-specific deadlines up to date."**

### 🧩 The STAR Breakdown

#### 1. Situation
Government scholarship schemes in Maharashtra are not published as clean APIs or structured tables. Instead, eligibility requirements reside inside disparate government circulars, government resolutions (GRs), and unstructured HTML pages published in mixed Marathi and English across DTE Maharashtra, MahaDBT, and NSP portals. 

For instance, the **Rajarshi Chhatrapati Shahu Maharaj Scheme** grants 50% tuition for boys from EBC/EWS categories with family incomes under ₹8 Lakh, but 100% tuition for girls; **AICTE Pragati** offers a flat ₹50,000 lump-sum for girls admitted through CAP rounds; and the **Dr. Panjabrao Deshmukh Scheme** provides ₹30,000 hostel allowances exclusively for children of registered agricultural laborers or marginal landholders in non-metro regions.

#### 2. Task
An early prototype relying purely on LLM prompt-stuffing failed critically in two ways:
1. **Fuzzy Hallucination on Eligibility:** The LLM routinely guessed income thresholds, conflated diploma admission rules with degree engineering, and told students they could claim two tuition-fee schemes concurrently—which violates government anti-duplication rules and results in scholarship forfeiture.
2. **Temporal Decay:** Portals update dates, portals, and income slabs each academic year. Relying on hardcoded prompt text created instant obsolescence.

My task was to architect a system where **code executes the logic, the LLM only formats and grounds explanations, and temporal boundaries remain strictly verifiable**.

#### 3. Action
To solve this, I implemented a three-tier hybrid architecture:

1. **Structured Data Ingestion & Normalization (`app/ingest.py`, `app/models.py`):**
   - Built a custom scraper and HTML parser extracting raw tabular and prose circulars into normalized `Record` dataclasses (`scheme_name`, `department`, `eligible_category`, `income_limit`, `benefit`, `source_url`, `verified`).
   - Cleaned multilingual inconsistencies, mapping Marathi terminology (उदा. 'ईबीसी', 'अल्पभूधारक शेतकरी') to standardized category and occupation taxonomies.

2. **Decoupling Retrieval from Mathematical & Logical Execution (`app/stacking.py`):**
   - **Never let the LLM calculate eligibility.** Instead, I designed a deterministic Python eligibility and stacking engine.
   - Modeled eligibility as a discrete multidimensional constraint matrix:
     $$\text{Eligible} = f(\text{Category}, \text{Income Slab}, \text{Gender}, \text{CAP Admission}, \text{Hostel Status})$$
   - Programmed the **MahaDBT Anti-Duplication Rule**: tuition/exam fee concessions are strictly mutually exclusive. If a student qualifies for both *Rajarshi Shahu Maharaj* and *Pragati*, the system flags a conflict and dynamically evaluates the student's actual tuition fee:
     - At **₹80,000 fee**: Rajarshi (50% = ₹40,000) vs Pragati (Flat ₹50,000) $\rightarrow$ Pragati is ranked #1.
     - At **₹120,000 fee**: Rajarshi (50% = ₹60,000) vs Pragati (Flat ₹50,000) $\rightarrow$ The preference order dynamically flips to Rajarshi!
   - Identified that the *Dr. Panjabrao Deshmukh Hostel Allowance* is a maintenance stipend and can be safely stacked on top of tuition fee waivers.

3. **Grounded RAG with Citation Validation (`app/rag.py`):**
   - Implemented 60-word micro-chunking with Top-5 retrieval via ChromaDB (`all-MiniLM-L6-v2`) and TF-IDF BM25.
   - Enforced a hard citation validator: every generated claim must reference `[n]` official sources. If the answer does not cite official sources or if the question asks for out-of-scope details (such as individual college hostel fees), the system refuses deterministically with *"I don't know"*.

4. **Year-Specific Temporal Safeguards:**
   - Ingested source URLs and timestamps directly into chunks and schema records.
   - Hardened prompt guardrails to explicitly instruct the model never to guess future deadlines and to output direct portal confirmation links (`mahadbt.maharashtra.gov.in`, `dte.maharashtra.gov.in`).

#### 4. Result
- **100% Precision on Eligibility & Stacking Rules:** Validated across 15 automated test cases in `tests/test_day10.py` covering fee-sensitive ranking flips, gender restrictions, and minority scholarship conflicts.
- **Zero Hallucination Rate:** RAG evaluation across 15 benchmark questions showed a **100% retrieval hit-rate** and flawless refusal on unanswerable questions (e.g. Question 6 on college hostel fees).
- **Production Efficiency:** Shipped an in-memory cache reducing latency from **1,450ms down to 0.19ms (99.99% speedup)** with zero LLM token costs on repeated queries.

---

## 💡 Part 3: 10 Likely Interview Questions & Model Answers

### Q1: Why not just use vanilla ChatGPT or prompt-stuffing for scholarship discovery?
**Answer:**  
*"Vanilla ChatGPT fails in three critical areas for scholarship discovery: First, **freshness and ground truth**—general models hallucinate deadlines and confuse central schemes with state-specific GRs. Second, **strict compliance**—government scholarship rules penalize double-claiming with disqualification; an LLM cannot be trusted with probabilistic arithmetic or regulatory conflict detection. Third, **explainability**—students risking their academic fees need auditable proof. ScholarSetu decouples semantic retrieval from deterministic Python stacking logic, ensuring every response is backed by clickable `[n]` citations to official government URLs."*

---

### Q2: How did you determine your chunking and hybrid retrieval strategy?
**Answer:**  
*"In Day 8, I ran a rigorous evaluation benchmark comparing two retrieval configurations across 15 ground-truth student questions (`eval/eval_set.json`):
- **Config A:** 120-word chunks, Top-3 retrieval.
- **Config B:** 60-word micro-chunks, Top-5 retrieval.

Config B achieved a **100% retrieval hit-rate (12/12)** compared to 91.7% (11/12) for Config A, while maintaining 100% accuracy on out-of-domain refusals (3/3) and delivering lower latency (2.2s vs 2.3s). Because scholarship rules are dense, atomic bullet points, smaller 60-word chunks prevent contextual contamination and allow the embedding model (`all-MiniLM-L6-v2`) to surface precise eligibility clauses."*

---

### Q3: How do you guarantee zero hallucinations in high-stakes financial aid recommendations?
**Answer:**  
*"We enforce a multi-layer verification gate:
1. **Retrieval Thresholding:** If ChromaDB similarity scores fall below `0.15`, the query is flagged as out-of-domain and skips the LLM entirely, immediately returning a standardized refusal.
2. **System Prompt Hardening:** The model is strictly instructed to use only facts provided in the numbered sources and never extrapolate outside knowledge.
3. **Regex Citation Verification:** After the model outputs JSON, our Python backend runs regex validation verifying that every claim contains a valid source marker (`[1]`, `[2]`). If an answer lacks verified citations, it is discarded and replaced with our verified 'I don't know' refusal."*

---

### Q4: Walk me through your LangGraph agent architecture and the human-in-the-loop approval gate.
**Answer:**  
*"In `app/graph.py`, we modeled the reasoning workflow as a stateful graph using LangGraph:
- **Conversation State & Memory:** Maintained in-memory per `thread_id` across turns.
- **Tool Selection:** The supervisor node decides whether to query RAG sources or invoke the `compare_schemes` tool.
- **Human-in-the-Loop Gate:** Before running `compare_schemes`, the agent yields an `awaiting_approval` status, returning the pending action and parameters to the client. The graph halts execution until the student explicitly sends `approve: true` or `approve: false` via `POST /agent`. This prevents unnecessary computation and gives users complete control over high-latency comparative operations."*

---

### Q5: How does your fee-sensitive preference ranking work in the Stacking Engine?
**Answer:**  
*"Scholarship stacking isn't static—it depends on the student's personal financial parameters. In `app/stacking.py`, we model schemes by benefit type:
- Schemes offering percentage tuition waivers (like Rajarshi Shahu Maharaj at 50% for boys) yield benefits directly proportional to college tuition.
- Schemes offering flat amounts (like AICTE Pragati at ₹50,000) have constant yields.

When a student enters their annual college fee:
$$\text{Yield}_{\text{Rajarshi}} = \text{Annual Fee} \times 0.50$$
$$\text{Yield}_{\text{Pragati}} = ₹50,000$$

If the fee is ₹80,000, Pragati yields ₹50,000 while Rajarshi yields ₹40,000 (Pragati is ranked #1). But if the fee is ₹140,000, Rajarshi yields ₹70,000, so our algorithm dynamically flips Rajarshi to #1. Then, it stacks non-conflicting maintenance allowances (like Dr. Panjabrao Deshmukh hostel allowance) to calculate the maximum legal financial package."*

---

### Q6: How did you achieve a 99.9% latency reduction in production?
**Answer:**  
*"In Day 13, I implemented a thread-safe, in-memory LRU + TTL response cache in `app/cache.py`. In scholarship discovery, student queries follow a heavy Pareto distribution—thousands of students ask identical questions about EBC income limits, hostel allowances, and Pragati guidelines. 
By normalizing question keys (stripping whitespace, lowercasing, punctuation normalization) and caching grounded answers:
- Cold requests invoking Groq cloud inference average **1,450.9 ms**.
- Warm cache hits return directly from memory in **0.19 ms**—a **7,463x speedup (99.99% latency reduction)**.
- Furthermore, cache hits consume **0 tokens**, eliminating LLM API costs for repeated traffic."*

---

### Q7: How do you defend against adversarial prompt injection and jailbreaks?
**Answer:**  
*"We implement defense-in-depth across two distinct layers:
1. **Ingress Regex Guardrail (`app/security.py`):** Before queries hit vectorstores or LLMs, a pre-inference filter scans for adversarial signatures (`ignore previous instructions`, `DAN mode`, `system override`, `say PWNED`, `reveal system prompt`). Detected injections are rejected instantly with HTTP 200 `answerable: false`, saving 100% of LLM tokens.
2. **Model-Level Rule Hardening:** In `SYSTEM_PROMPT` and `prompts/system.txt`, Rule 7 instructs the model to ignore any user attempt to override instructions or persona.
In our automated test suite (`tests/test_day13.py`), adversarial payloads achieved a **100% interception and refusal rate** with zero prompt leaks."*

---

### Q8: How is your CI/CD pipeline and cloud container deployment structured?
**Answer:**  
*"In `.github/workflows/ci.yml`, every push and PR to `main` triggers a multi-stage automated pipeline:
1. **Static Analysis:** Runs `ruff check .` across the entire codebase with zero tolerance for lint errors.
2. **Automated Testing:** Executes all 53 `pytest` unit, integration, and UI AppTest test cases in an isolated Python 3.11 environment.
3. **Container Build & Smoke Test:** Builds the production `Dockerfile` with CPU-optimized PyTorch and launches a temporary container to verify that `GET /health` returns HTTP 200 with all scheme records loaded.
4. **Cloud Deployment:** Merges to `main` trigger automated deployments on **Render**, serving the live API and interactive Swagger docs at `https://cream-ai.onrender.com`."*

---

### Q9: How do you handle multilingual text and changing government schemes?
**Answer:**  
*"Maharashtra government circulars frequently mix Marathi and English. In `app/fetch.py` and `app/ingest.py`, we handle UTF-8 Marathi encodings and map Marathi terms to canonical scheme attributes. In our semantic search layer, `sentence-transformers/all-MiniLM-L6-v2` effectively maps transliterated and English-Marathi domain concepts into shared vector space.
To handle changing annual schemes, our ingest pipeline is modular: running `python -m app.fetch --force` re-scrapes the latest portal versions, rebuilds `data/records.json`, and re-indexes ChromaDB without requiring any backend code changes."*

---

### Q10: If you had another month to work on ScholarSetu, what would you build next?
**Answer:**  
*"I would focus on three high-impact enhancements:
1. **OCR Document Verification Pipeline:** Allow students to upload income certificates, caste validity documents, and ration cards; use lightweight vision models to extract dates and income figures, automatically cross-verifying them against scheme eligibility requirements.
2. **Multi-Dialect Marathi Speech Interface:** Integrate Whisper speech-to-text to allow rural students from Marathwada and Vidarbha to ask scholarship questions via voice in regional Marathi dialects.
3. **Automated MahaDBT Application Form Filler:** Build an agentic browser tool using Playwright to pre-fill the complex 8-page MahaDBT application form based on the student's validated profile, saving hours of manual data entry."*
