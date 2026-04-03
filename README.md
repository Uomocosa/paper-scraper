# Local AI Scientific Paper Pipeline 🤖📄

This repository contains a local, automated "snowballing" literature review agent. The pipeline is designed to take a set of seed scientific papers, extract their references, legally download the PDFs of those references, parse them into machine-readable text, and run a local Large Language Model (LLM) to extract answers to specific research questions.

## 🎯 Architecture & Phases

The system operates strictly locally (with the exception of API calls to open science databases for metadata/downloads) to avoid publisher rate limits and ensure data privacy.

### Phase 1: The Citation Extractor
* **Goal:** Extract references from seed PDFs reliably.
* **Tool:** **Grobid** (running locally via Docker).
* **Action:** Uses the `/api/processReferences` endpoint to extract structured bibliographies from seed PDFs, returning DOIs (Digital Object Identifiers) for every cited paper.

### Phase 2: Crawler & Downloader
* **Goal:** Download the referenced papers.
* **Tools:** Python + **Semantic Scholar API** (or **OpenAlex API**).
* **Action:** Queries the API using the DOIs from Phase 1 to find `openAccessPdf` links. Downloads the PDFs legally bypassing paywalls and saves them to the `Downloaded_Papers/` directory.

### Phase 3: The AI Batch Processor (Prompt Loop)
* **Goal:** Convert PDFs to text and prompt the AI.
* **Tools:** **Marker** (or **MinerU**) + **Ollama** (Local LLM).
* **Action:** 1. Reads the prompt/question from `Question_1.md`.
  2. Iterates through `Downloaded_Papers/`, using Marker to parse multi-column PDFs and equations into clean Markdown.
  3. Sends the prompt + parsed text to a local LLM via Ollama.
  4. Saves the LLM's analysis into the `Response_1/` directory as `<paper_nickname>.md`.

### Phase 4: "Smart Filter" (Future Implementation)
* **Goal:** Evaluate the relevance of "references of references" *before* downloading to save compute and storage.
* **Tool:** Ollama Structured Outputs (JSON mode).
* **Action:** Prompts the AI to read a paper's abstract and return `{"relevant": true/false}`. If true, it triggers Phase 2 for that new paper.

---

## 📂 Directory Structure

\`\`\`text
├── Downloaded_Papers/      # Raw PDFs downloaded from Open Access APIs
├── Response_1/             # AI-generated markdown responses for each paper
├── Seed_Papers/            # The initial PDFs fed into the pipeline manually
├── Question_1.md           # The prompt/question the AI must answer for every paper
├── extract_refs.py         # Script to interact with Grobid
├── download_pdfs.py        # Script to query OpenAlex/Semantic Scholar and download
├── batch_process.py        # Script to orchestrate Marker/MinerU and Ollama
├── docker-compose.yml      # Setup for Grobid container
└── README.md
\`\`\`

## 🛠️ Prerequisites & Setup

To run this pipeline, you will need the following installed:

1. **Python 3.10+**
2. **Docker:** Required to run the Grobid image locally.
    ```bash
    docker pull lfoppiano/grobid:latest
    docker run -t --rm -p 8070:8070 lfoppiano/grobid:latest
    ```
3. **Ollama:** For running the local LLM. 
    * *Hardware Note:* Because this pipeline feeds entire papers into the context window, a GPU with sufficient VRAM is required.
    * *Recommended Models:* `llama3` (8B context-extended) or `mistral-nemo` (128k native context window).
4. **PDF Parsers:**
    * Install [Marker](https://github.com/VikParuchuri/marker) or [MinerU](https://github.com/opendatalab/MinerU) for high-fidelity PDF-to-Markdown conversion.

## 🚀 Getting Started

*(Instructions to be added as scripts are developed)*
1. Place your starting papers in `Seed_Papers/`
2. Write your research question in `Question_1.md`
3. Run the extraction, download, and processing scripts...
