# Delfa Bridge 🌉
### Intelligent Middleware for Enterprise AI | Powered by Panohayan™

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-green)](https://supabase.com)
[![Docling](https://img.shields.io/badge/Docling-2.x-orange)](https://github.com/DS4SD/docling)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

Delfa Bridge closes the gap between chaotic enterprise documents and professional-grade AI agents. Through the **Panohayan™ architecture**, it transforms unstructured data — PDFs, Word, Excel, ERPs, APIs — into a structured, auditable, and AI-ready Entity Data Brain.

---

## 🧠 Panohayan™ Architecture
```
Document (PDF, DOCX, XLSX, ERP, API)
        ↓
[DOCLING] — Universal document conversion + OCR
        ↓
[CONTENT CLASSIFIER] — Tables? Narrative? Both?
        ↓              ↓
  [LlamaIndex]    [LangExtract]
  Tabular data    Semantic entities
        ↓              ↓
        └──── [IHS MERGE] ────┘
         Hash-based deduplication
        ↓
[MODEL ROUTER] — Cost-efficient LLM selection
  Tier 1: Gemini 2.0 Flash    (simple docs)
  Tier 2: Gemini 2.5 Flash    (tables / long)
  Tier 3: Claude Sonnet       (legal / fiscal)
  Tier 4: Claude Opus         (deep reasoning)
        ↓
[EDB LITE] — Supabase + pgvector semantic memory
[GRG]      — Governance Guardrails
[TM]       — Traceability Matrix (full audit trail)
```

---

## ✨ Key Features

- **Zero hallucination** — GRG ensures every AI response is grounded in verified, traceable data
- **Full traceability** — TM logs every decision back to its document source
- **Data sovereignty** — knowledge lives in the client's database, not in the model
- **Format agnostic** — PDF, DOCX, XLSX, scanned images, ERPs, REST APIs
- **Cost-efficient** — Model Router selects the cheapest LLM that meets quality requirements
- **Multi-tenant** — org_id isolation via Supabase RLS from day one

---

## 🏗️ The 4 Pillars

| Component | Name | Role |
|-----------|------|------|
| DII | Digest Input Intelligence | Document ingestion pipeline |
| EDB | Entity Data Brain Lite | Hybrid relational + vector memory |
| GRG | Governance Guardrails | Configurable governance rules |
| TM | Traceability Matrix | Complete audit trail |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Document conversion | Docling 2.x (PDF, DOCX, XLSX, OCR) |
| Tabular extraction | LlamaIndex |
| Semantic extraction | LangExtract + Gemini |
| Model routing | Custom Python Model Router |
| LLMs | Gemini Flash/Pro, Claude Sonnet/Opus, GPT-4o |
| Vector storage | Supabase + pgvector |
| API | FastAPI (coming soon) |
| Deployment | Docker + Railway (coming soon) |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Supabase account with pgvector enabled
- Google API Key (Gemini)
- OpenAI API Key (embeddings)

### Installation
```bash
git clone https://github.com/JorgeAmparan/delfa-bridge-core.git
cd delfa-bridge-core

python3.11 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Environment Setup
```bash
cp .env.example .env
# Edit .env with your API keys
```

### Run DII Pipeline
```bash
# Place your documents in the data/ folder
python3 app/core/dii.py
```

---

## 📁 Project Structure
```
delfa-bridge-core/
├── app/
│   ├── core/
│   │   ├── dii.py        # DII — Document ingestion pipeline
│   │   ├── edb.py        # EDB Lite — Semantic memory
│   │   ├── grg.py        # GRG — Governance guardrails
│   │   ├── matrix.py     # TM — Traceability matrix
│   │   ├── mr.py         # Model Router
│   │   └── main.py       # Main orchestrator
│   └── connectors/       # External connectors (Drive, MicroSip, etc.)
├── data/                 # Documents directory (gitignored)
├── CLAUDE.md             # AI context instructions
├── DelfaBridge_Blueprint_v1.md  # Architecture blueprint
├── .env.example          # Environment template
└── README.md
```

---

## 🗺️ Roadmap

- [x] DII v2 — Docling + LangExtract + LlamaIndex + Model Router
- [x] Supabase schema — 5 tables + pgvector + RLS
- [ ] EDB Lite — semantic search with embeddings
- [ ] GRG — configurable governance rules
- [ ] TM — centralized audit logger
- [ ] FastAPI REST endpoints
- [ ] Connectors — Google Drive, MicroSip ERP, SQL
- [ ] Docker microservices + MCP servers
- [ ] Railway deployment
- [ ] Commercial landing + Stripe subscriptions

---

## 🏢 About

**Delfa Bridge** is built on **Panohayan™** architecture, proprietary IP by Jorge Luis Amparán Hernández / Lappicero Studio.

Licensed exclusively to Juan del Hoyo for commercial use under Delfa Bridge.

---

*Built in Ciudad Juárez, México 🇲🇽 — at the heart of the T-MEC industrial corridor*
