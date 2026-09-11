# MIRA — Multi-Modal Intelligent Retrieval & Automation

<p align="center">
  <strong>SIH26117 — Sovereign On-Premise Agentic AI Workbench</strong>
</p>

<p align="center">
  <em>AI for confidential industrial knowledge work — without sending sensitive data to the cloud.</em>
</p>

<p align="center">

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Ollama](https://img.shields.io/badge/Inference-Ollama-black?logo=ollama)
![RAG](https://img.shields.io/badge/RAG-Hybrid-purple)
![SIH](https://img.shields.io/badge/Smart%20India%20Hackathon-SIH26117-orange)

</p>

---

## 🎥 Project Demo

<p align="center">
  <a href="https://www.youtube.com/watch?v=4nxJA_CDFIo">
    <img src="https://img.youtube.com/vi/4nxJA_CDFIo/maxresdefault.jpg" alt="MIRA — SIH26117 Project Demo" width="850">
  </a>
</p>

<p align="center">
  <strong>▶ Click the thumbnail to watch the complete MIRA demonstration on YouTube.</strong>
</p>

**Demo:** https://www.youtube.com/watch?v=4nxJA_CDFIo


## 🎥 Demo Video

### ▶️ MIRA — SIH26117 Project Demonstration

Watch the complete demonstration of MIRA, including its agentic workflow, hybrid retrieval, controlled tool execution, document generation, audit trail, and network-isolation demonstration.

**YouTube:**  
👉 https://www.youtube.com/watch?v=4nxJA_CDFIo

<!--
Recommended format:

[![MIRA — SIH26117 Demo](https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=VIDEO_ID)

Replace VIDEO_ID with the ID of your YouTube video.
-->

---

# 🚨 Problem Statement

Industrial organizations such as refineries, PSUs, defence organizations, and other critical infrastructure operators work with highly sensitive technical information.

This information can include:

- Standard Operating Procedures (SOPs)
- Incident reports
- Maintenance records
- Equipment histories
- Engineering documents
- HAZOP records
- Management of Change (MOC) documents
- Shift handovers
- Work orders
- Equipment drawings
- Technical calculations
- Scanned and handwritten documents

Modern cloud-based AI assistants can significantly improve knowledge work, but confidential industrial information cannot simply be sent to external AI services.

This creates a fundamental challenge:

> **How can organizations use modern AI capabilities while keeping sensitive information inside their own controlled infrastructure?**

SIH26117 focuses on building a sovereign AI solution capable of operating within environments where data confidentiality, sovereignty, and network isolation are critical.

---

# 💡 Our Solution — MIRA

## Multi-Modal Intelligent Retrieval & Automation

**MIRA** is an on-premise agentic AI workbench designed for confidential industrial knowledge workflows.

Instead of sending sensitive documents to external cloud AI services, MIRA is designed to keep the core AI workflow within the organization's infrastructure.

The system combines:

- Local LLM inference
- Agentic orchestration
- Hybrid Retrieval-Augmented Generation
- Exact equipment/document tag matching
- OCR
- Multimodal document processing
- Controlled Python execution
- Human approval gates
- Provenance tracking
- Hash-chained audit logging
- Process-level network isolation
- Automated professional document generation

MIRA is therefore designed as more than a chatbot.

It can retrieve evidence, reason over information from multiple documents, invoke tools, perform controlled calculations, request human approval, and generate structured deliverables.

---

## ⚡ Executive Snapshot

| Dimension | MIRA |
|---|---|
| **Deployment** | Sovereign / on-premise |
| **AI Runtime** | Local Ollama inference |
| **Retrieval** | Dense + BM25 + exact-tag hybrid RAG |
| **Input Types** | PDF, DOCX, XLSX, images, scanned/handwritten documents |
| **Agent Control** | Human approval for sensitive operations |
| **Execution Safety** | Controlled Python sandbox |
| **Network Control** | Process-level outbound network guard |
| **Traceability** | Provenance + SHA-256 hash-chained audit |
| **Outputs** | DOCX, XLSX, PPTX, PDF, PNG |
| **Evaluation** | 15 golden questions + synthetic industrial corpus |

> **MIRA is designed as a controlled AI workbench, not merely a chatbot.**

---

# 🏗️ System Architecture

```text
                         ┌─────────────────────────┐
                         │       User / Engineer   │
                         │      Streamlit Browser  │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │    Agent Orchestration  │
                         │        agent.py         │
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
             ┌────────────┐   ┌──────────────┐   ┌─────────────┐
             │ Local LLM  │   │  Hybrid RAG  │   │    Tools    │
             │   Ollama   │   │  Knowledge   │   │             │
             └─────┬──────┘   │     Base     │   └──────┬──────┘
                   │          └──────┬───────┘          │
                   │                 │                  │
                   │        ┌────────┼────────┐         │
                   │        │        │        │         │
                   │        ▼        ▼        ▼         ▼
                   │      Dense    BM25    Exact      Sandbox
                   │      Search   Search   Tags
                   │        │        │        │
                   │        └────────┼────────┘
                   │                 ▼
                   │                RRF
                   │                 │
                   └─────────────────┼──────────────────┐
                                     ▼                  │
                          ┌──────────────────────┐      │
                          │ Provenance & Audit    │◄─────┘
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │  Generated Outputs   │
                          │ DOCX/XLSX/PPTX/PDF   │
                          │        /PNG          │
                          └──────────────────────┘
```

---

# ✨ Key Features

## 🧠 1. Local Agentic AI

MIRA uses a hand-written agent orchestration loop to coordinate reasoning and tool execution.

The agent can:

1. Understand the user's request
2. Retrieve relevant evidence
3. Decide which tools are required
4. Perform multi-step operations
5. Pause for human approval when required
6. Execute approved operations
7. Generate a final response or deliverable
8. Record execution information in the audit trail

---

## 🔍 2. Hybrid RAG

Industrial knowledge bases contain identifiers where exact matching is extremely important.

For example:

```text
P-2104A
P-2104B
```

These two equipment tags are semantically very similar, but they represent different assets.

A purely semantic retrieval system can therefore produce undesirable results.

MIRA combines three retrieval approaches:

```text
             ┌─────────────────────┐
             │ Dense Semantic      │
             │ Search              │
             └──────────┬──────────┘
                        │
             ┌──────────▼──────────┐
             │ BM25 Keyword Search │
             └──────────┬──────────┘
                        │
             ┌──────────▼──────────┐
             │ Exact Tag Matching  │
             └──────────┬──────────┘
                        │
                        ▼
              Reciprocal Rank
                 Fusion (RRF)
                        │
                        ▼
              Ranked Retrieval
```

This approach is particularly useful for technical information containing:

- Equipment tags
- Document IDs
- Work-order IDs
- MOC numbers
- SOP identifiers
- Component codes

---

# 👁️ 3. Multimodal Document Processing

Industrial information is not always available as machine-readable text.

MIRA's document pipeline supports information from:

- PDFs
- DOCX files
- XLSX files
- Images
- Scanned documents
- Handwritten documents
- Engineering drawings

The extraction pipeline includes OCR support and a vision-model pathway for image-based information.

---

# 📄 4. Structure-Aware Document Processing

MIRA's chunking pipeline is designed for technical documents rather than blindly splitting text.

It considers structures such as:

- Headings
- Tables
- Numbered steps
- Document sections
- Technical identifiers

The pipeline also includes OCR-related equipment-tag repair mechanisms to improve retrieval of technical identifiers.

---

# 🛡️ 5. Human Approval Gate

MIRA follows a human-in-the-loop approach for sensitive operations.

```text
AI proposes action
       │
       ▼
Human Approval
       │
   ┌───┴───┐
   │       │
 APPROVE  REJECT
   │       │
   ▼       ▼
Execute   Stop
```

This provides an additional layer of control over potentially consequential tool operations.

---

# 🔐 6. Controlled Python Sandbox

MIRA includes a controlled execution environment for Python operations proposed by the AI.

The prototype uses multiple layers of protection:

```text
Generated Code
      │
      ▼
AST Static Analysis
      │
      ▼
Import Restrictions
      │
      ▼
Runtime Import Guard
      │
      ▼
Subprocess Isolation
      │
      ▼
Resource Limits
      │
      ▼
Execution
```

The sandbox is intended as an application-level security mechanism for the prototype.

For production deployment, stronger operating-system and container-level isolation should additionally be used.

---

# 🌐 7. Network Isolation / Air-Gap Guard

MIRA includes a process-level network guard.

The guard restricts outbound socket connections while allowing required local loopback communication for services running on the same machine.

The application also provides a self-test for demonstrating blocked external connections.

### Important

The network guard is a **process-level prototype control**.

It should not be interpreted as a replacement for:

- Host firewalls
- Network segmentation
- OS security policies
- Container isolation
- Physically air-gapped infrastructure

A production deployment should use these controls in combination with application-level protections.

---

# 🔗 8. Provenance & Hash-Chained Audit

MIRA uses SHA-256 hash chaining for an auditable sequence of events.

```text
Event 1
   │
   ▼
Hash 1
   │
   ▼
Event 2 + Hash 1
   │
   ▼
Hash 2
   │
   ▼
Event 3 + Hash 2
   │
   ▼
Hash 3
```

This makes the audit trail tamper-evident and allows the chain to be verified.

---

# 📑 9. Professional Output Generation

MIRA is designed to produce useful deliverables rather than stopping at a conversational response.

Supported output formats include:

| Format | Purpose |
|---|---|
| DOCX | Technical reports |
| XLSX | Structured data and analysis |
| PPTX | Presentations |
| PDF | Formal reports |
| PNG | Visualizations / charts |

Generated outputs can contain provenance information and audit-related metadata.

---

# 🏭 Flagship Industrial Workflow

The project includes a synthetic refinery knowledge base containing interconnected technical documents.

A representative investigation focuses on:

```text
P-2104B
```

A typical workflow is:

```text
User Question
      │
      ▼
Agent
      │
      ▼
Knowledge Retrieval
      │
      ├── Semantic Search
      ├── BM25
      └── Exact Tag Match
      │
      ▼
Relevant Evidence
      │
      ▼
Cross-Document Reasoning
      │
      ▼
Calculation / Tool Use
      │
      ▼
Human Approval
      │
      ▼
Generated Report
      │
      ▼
Provenance + Audit
```

---

# 📊 Demonstration Scenario

The synthetic corpus contains the following vibration progression for **P-2104B**:

| Month | Vibration |
|---|---:|
| January | 3.9 mm/s RMS |
| February | 4.0 mm/s RMS |
| March | 4.1 mm/s RMS |
| April | 4.6 mm/s RMS |
| May | 5.2 mm/s RMS |
| June | 6.4 mm/s RMS |
| July | 7.8 mm/s RMS |
| August | 9.6 mm/s RMS |

The demonstration corpus defines:

```text
Alert Level : 7.1 mm/s RMS
Trip Level  : 11 mm/s RMS
```

Additional synthetic documents provide connected context around:

- The equipment incident
- Mechanical seal failure
- Maintenance activity
- Work orders
- Engineering recommendations
- Management of Change
- Spare availability
- Operational restrictions
- Shift handover information

The purpose is to demonstrate **multi-document industrial reasoning** rather than simple question answering.

---

# 🧰 Technology Stack

| Layer | Technology |
|---|---|
| Language | Python |
| User Interface | Streamlit |
| Local Inference | Ollama |
| Text / Reasoning Model | Qwen2.5 |
| Vision Model | Qwen2.5-VL |
| Embedding Model | Nomic Embed |
| Retrieval | Dense + BM25 + Exact Tag |
| Ranking | Reciprocal Rank Fusion |
| OCR | Tesseract |
| Document Processing | PDF / DOCX / XLSX / Images |
| Agent | Custom Python orchestration |
| Code Execution | Controlled Python sandbox |
| Security | Process-level network guard |
| Audit | SHA-256 hash chain |
| Outputs | DOCX / XLSX / PPTX / PDF / PNG |

---

# 📁 Project Structure

```text
sih26117-mira/
│
├── README.md
├── .gitignore
├── requirements.txt
│
├── app.py
├── agent.py
├── config.py
│
├── core/
│   ├── audit.py
│   ├── chunker.py
│   ├── extract.py
│   ├── kb.py
│   ├── llm.py
│   ├── netguard.py
│   ├── outputs.py
│   └── sandbox.py
│
├── scripts/
│   ├── corpus_spec.py
│   └── build_*.py
│
├── data/
│   ├── documents/
│   └── eval/
│
├── docs/
│   ├── implementation-plan.md
│   ├── team-onboarding.md
│   ├── demo-script.md
│   ├── presentation/
│   └── examples/
│
└── .streamlit/
    └── config.toml
```

---

# 🚀 Installation & Setup

## Prerequisites

Before running MIRA, install:

- Python 3.x
- Ollama
- Tesseract OCR
- Required Python dependencies
- Local models required by the configuration
- Suitable local compute for the selected models

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR-USERNAME/sih26117-mira.git
cd sih26117-mira
```

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scriptsctivate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 4. Install Ollama

Install Ollama and ensure that its local service is running.

The intended model configuration includes:

```text
qwen2.5:7b-instruct
qwen2.5vl:7b
nomic-embed-text
```

On systems with lower available VRAM, an appropriate smaller vision-model variant can be configured.

## 5. Pull the Models

```bash
ollama pull qwen2.5:7b-instruct
ollama pull qwen2.5vl:7b
ollama pull nomic-embed-text
```

Verify:

```bash
ollama list
```

## 6. Install Tesseract OCR

Verify:

```bash
tesseract --version
```

## 7. Build the Knowledge Base

The repository contains a synthetic industrial corpus under:

```text
data/documents/
```

Build the local search index using the project's indexing scripts.

The knowledge base combines semantic retrieval, BM25, and exact equipment/document tag matching.

## 8. Start the Application

```bash
streamlit run app.py
```

The MIRA interface will then be available through the local browser.

---

# 🖥️ Application Modules

### 💬 Chat
Interact with the MIRA agent and perform knowledge-work tasks.

### 📚 Knowledge Base
Inspect the indexed document corpus and retrieval system.

### 🛡️ Trust & Audit
Inspect audit information, provenance, and verification status.

### 🔒 Air-Gap
Run the network isolation self-test and demonstrate blocked external communication.

---

# 🧪 Evaluation

MIRA includes **15 golden evaluation questions** located at:

```text
data/eval/golden_questions.json
```

These questions are designed around the synthetic industrial corpus and evaluate the system's ability to retrieve and reason over connected information.

---

# 📚 Synthetic Dataset

The repository contains a synthetic refinery corpus covering:

- Pump changeover SOP
- Mechanical seal failure incident
- HAZOP action register
- Hot-work restrictions
- Monthly operations report
- Engineering practices
- Management of Change (MOC)
- Vibration history
- Work-order history
- Critical spares
- Operator training matrix
- Scanned shift handover
- Engineering schematic / P&ID

### ⚠️ Data Disclaimer

**All industrial documents contained in this repository are synthetic demonstration documents.**

They were created for the SIH26117 prototype and do **not** contain confidential or proprietary MRPL operational data.

Do not upload real confidential industrial documents to this public repository.

---

# 🔏 Sovereignty by Design

Traditional cloud-based AI workflows often look like:

```text
Sensitive Documents
        │
        ▼
     Internet
        │
        ▼
External AI Service
```

MIRA instead follows an on-premise architecture:

```text
Sensitive Documents
        │
        ▼
Organization Infrastructure
        │
        ├── Local LLM
        ├── Local Vision Model
        ├── Local Embeddings
        ├── Local Knowledge Base
        ├── Local Tools
        └── Local Audit
```

The goal is to keep sensitive industrial information within the organization's controlled environment.

---

# 📈 Why MIRA?

| Challenge | MIRA Approach |
|---|---|
| Sensitive data cannot leave the organization | Local/on-premise inference |
| Cloud AI dependency | Ollama-based local models |
| Technical document retrieval | Hybrid RAG |
| Similar equipment identifiers | Exact tag matching |
| Scanned documents | OCR |
| Visual/engineering information | Vision-model pathway |
| AI-generated code | Controlled sandbox |
| Sensitive actions | Human approval |
| Traceability | Provenance + audit |
| Tamper evidence | SHA-256 hash chain |
| External network communication | Process-level network guard |
| Need for formal deliverables | DOCX/XLSX/PPTX/PDF/PNG generation |

---

# 🗺️ Future Roadmap

## Phase 1 — Prototype

- Local LLM inference
- Hybrid RAG
- Multimodal document processing
- OCR
- Human approval
- Controlled Python execution
- Provenance
- Hash-chained audit
- Network isolation demonstration
- Professional output generation

## Phase 2 — Production Hardening

- Containerized sandbox
- Stronger OS-level isolation
- Multi-user authentication
- Role-based access control
- Additional local models
- Expanded evaluation framework
- Enterprise deployment controls
- Production observability

## Phase 3 — Enterprise Deployment

Potential application areas include:

- Refineries
- Manufacturing
- Defence organizations
- Public-sector enterprises
- Critical infrastructure
- Other confidentiality-sensitive industrial environments

---

# 🎯 SIH26117 Alignment

| SIH Requirement / Challenge | MIRA Implementation |
|---|---|
| Confidential industrial information | On-premise architecture |
| Sovereign AI | Local model inference |
| Intelligent knowledge retrieval | Hybrid RAG |
| Technical identifiers | Exact tag matching |
| Multimodal information | OCR + vision pathway |
| Agentic workflows | Custom agent orchestration |
| Controlled execution | Python sandbox |
| Human oversight | Approval gate |
| Auditability | Hash-chained audit |
| Provenance | Source/output provenance |
| Network isolation | Process-level network guard |
| Professional deliverables | Multi-format generation |

---

# 🤝 Team Collaboration

This repository follows a Git-based feature branch workflow.

```text
main
 │
 ├── feature/agent
 ├── feature/rag
 ├── feature/ui
 ├── feature/security
 └── feature/testing
```

### Recommended workflow

```bash
git checkout main
git pull origin main

git checkout -b feature/your-feature

# Make changes

git add .
git commit -m "Describe your changes"

git push -u origin feature/your-feature
```

Then create a Pull Request and merge into `main` after review.

### Important

Please avoid making direct changes to `main`.

This keeps the team's work organized and reduces merge conflicts.

---

# 📖 Documentation

Additional project documentation is available under:

```text
docs/
```

including:

- Implementation architecture
- Team onboarding guide
- Demo script
- Presentation material
- Example outputs

---

# ⚠️ Prototype Disclaimer

MIRA is a **Smart India Hackathon prototype** created to demonstrate the feasibility of sovereign agentic AI for confidential industrial knowledge workflows.

It is not intended to replace:

- Industrial safety procedures
- Engineering approval processes
- Cybersecurity controls
- Operational decision-making
- Qualified human expertise

The following points are particularly important:

1. The industrial corpus included in this repository is synthetic.
2. The Python sandbox is an application-level prototype.
3. The network guard operates at the application-process level.
4. Production deployment requires stronger OS, container, and network security controls.
5. AI-generated recommendations should be reviewed by qualified personnel before operational use.

---

# 🌟 Vision

> **AI should not require organizations to surrender control of their data.**

MIRA explores a different approach:

### Bring intelligence to the data — not the data to the intelligence.

By combining:

**Local AI + Multimodal Retrieval + Agentic Workflows + Human Oversight + Controlled Execution + Provenance + Auditability**

MIRA aims to make advanced AI practical for organizations where confidentiality and data sovereignty are non-negotiable.

---

# 🏆 Smart India Hackathon

| | |
|---|---|
| **Hackathon** | Smart India Hackathon |
| **Problem Statement** | SIH26117 |
| **Project** | MIRA — Multi-Modal Intelligent Retrieval & Automation |
| **Category** | Sovereign On-Premise Agentic AI Workbench |

---

# 🎥 Watch the Demo

### MIRA — SIH26117

👉 **[Watch the complete project demonstration on YouTube](https://www.youtube.com/watch?v=4nxJA_CDFIo)**

---

<p align="center">

<strong>MIRA</strong>

<br>

<em>Sovereign • Agentic • Auditable</em>

<br><br>

Built for confidential industrial knowledge work.

</p>
