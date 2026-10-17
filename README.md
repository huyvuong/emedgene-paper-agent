# Emedgene-Style Clinical Literature NLP Extraction & Grounding Agent (`emedgene-paper-agent`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP Ready](https://img.shields.io/badge/MCP-FastMCP-purple.svg)](https://modelcontextprotocol.io/)

A working reference architecture and prototype that replicates how **Illumina's Emedgene** transforms unstructured peer-reviewed clinical genetics literature (PDFs or PubMed IDs) into **Explainable AI (XAI) clinical evidence**.

Instead of treating a scientific paper solely as a static text blob for RAG, this pipeline turns a peer-reviewed article into an **active clinical curation agent** by:
1. **Layout-Aware Document Parsing:** Preserving section headers (`Abstract`, `Results / Case_Report`, `Table`, `Functional_Assay`) from local PDFs (`Docling` / `pypdf`) or live NCBI **PubTator3 BioC-JSON** streams.
2. **Structured GDVP NLP Extraction:** Extracting verified **Gene–Disease–Variant–Phenotype (GDVP)** assertions with ACMG/AMP evidence codes (`PVS1`, `PS2`, `PS3`, `PM1`) and **verbatim sentence-level provenance**.
3. **Deterministic Ontology Grounding:** Resolving extracted mentions against live biomedical APIs—**MyGene.info** (`HGNC`), **EBI OLS4** (`MONDO` and `HPO`)—and deterministically verifying verbatim quotes against the source text (`quote_verified: true`).
4. **Agentic Tool Exposure (FastMCP):** Wrapping the grounded knowledge graph in callable MCP tools (`query_variant_evidence`, `match_patient_phenotypes`, `evaluate_acmg_criteria`) for downstream variant interpretation workflows.

---

## 1. Architectural Blueprint

```text
[Peer-Reviewed Article (Local PDF or PubMed PMID)]
       │
       ▼
[1. Layout-Aware Parsing] ──► Docling / pypdf / NCBI PubTator3 BioC API (Preserves Sections + Tables)
       │
       ▼
[2. Hybrid NLP Extraction] ──► PubTator3 Candidate NER + Gemini Structured Outputs (GDVP + ACMG Tags)
       │
       ▼
[3. Ontology Grounding]   ──► MyGene.info (HGNC), EBI OLS4 REST API (HPO & MONDO), Substring Quote Verifier
       │
       ▼
[4. Paper Agent Server]   ──► FastMCP Server exposing structured ACMG assertions, phenotype overlap & provenance
```

| Layer | Responsibility | Implementation |
| :--- | :--- | :--- |
| **Document Parsing** | Extracts full text and variant tables while tracking section headers (`Results`, `Case_Report`, `Functional_Assay`). | [`src/emedgene_agent/parser.py`](src/emedgene_agent/parser.py) (`Docling` / `pypdf` + NCBI PubTator3 BioC API) |
| **Data Contracts** | Strict Pydantic v2 schemas for GDVP assertions, HGVS variants, and ACMG tags. | [`src/emedgene_agent/schemas.py`](src/emedgene_agent/schemas.py) |
| **Entity & Relation NLP** | Binds genes, variants, phenotypes, zygosity, inheritance origin, and functional assays into proband assertions. | [`src/emedgene_agent/extractor.py`](src/emedgene_agent/extractor.py) (`google-genai` + deterministic offline fallback) |
| **Biomedical Grounding** | Resolves raw strings (`SCN1A`, `Dravet syndrome`, `generalized tonic-clonic seizures`) to canonical IDs (`HGNC:10585`, `MONDO:0011073`, `HP:0002069`). | [`src/emedgene_agent/grounder.py`](src/emedgene_agent/grounder.py) (Live EBI OLS4 & MyGene.info APIs) |
| **Agent Interface** | Exposes the curated paper as an interactive MCP tool server. | [`src/emedgene_agent/mcp_server.py`](src/emedgene_agent/mcp_server.py) (`FastMCP`) |

---

## 2. Project Structure

```text
pdf_NLP_extract_emedgene/
├── paper_to_gdvp_agent.py               # Standalone CLI & quickstart entrypoint
├── pyproject.toml                       # Package metadata, dependencies & CLI script
├── requirements.txt                     # Standard pip/uv dependency list
├── .env.example                         # Environment variable template (GEMINI_API_KEY)
├── samples/
│   ├── PMID_11359211_SCN1A_Dravet.pdf   # Real-world sample clinical genetics PDF article
│   └── expected_output_11359211.json    # Grounded GDVP knowledge base output
├── scripts/
│   └── generate_sample_pdf.py           # Generates the sample clinical PDF with variant table
├── src/
│   └── emedgene_agent/
│       ├── __init__.py
│       ├── schemas.py                   # Pydantic v2 GDVP & ACMG schemas
│       ├── parser.py                    # PDF & NCBI PubTator3 BioC parser
│       ├── extractor.py                 # Gemini structured NLP extractor + fallback
│       ├── grounder.py                  # EBI OLS4 (HPO/MONDO) & MyGene.info (HGNC) grounder
│       ├── mcp_server.py                # FastMCP server & clinical agent tools
│       └── cli.py                       # CLI runner
└── tests/
    └── test_pipeline.py                 # End-to-end pytest suite
```

---

## 3. Quickstart

### Installation

Using `uv` (recommended) or `pip`:

```bash
uv venv --python 3.11
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

uv pip install -e ".[dev]"
```

*(Optional)* Set your `GEMINI_API_KEY` to use live Gemini structured extraction (if omitted, the pipeline automatically uses its built-in deterministic clinical NLP extractor while still querying live NCBI PubTator3, EBI OLS4, and MyGene.info APIs):

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY="AIza..."
```

---

## 4. Usage Examples

### A. Run on a Real-World PubMed ID (`--pmid`)

Fetch pre-annotated biomedical entities from **NCBI PubTator3** and extract grounded GDVP assertions for **PMID: 11359211** (*Claes et al., De Novo Mutations in the Sodium-Channel Gene SCN1A Cause Severe Myoclonic Epilepsy of Infancy*):

```bash
python paper_to_gdvp_agent.py --pmid 11359211
```

### B. Run on a Local Peer-Reviewed Journal PDF (`--pdf`)

Extract directly from the included multi-section clinical PDF (`samples/PMID_11359211_SCN1A_Dravet.pdf`) and save the grounded JSON knowledge base:

```bash
python paper_to_gdvp_agent.py \
  --pdf samples/PMID_11359211_SCN1A_Dravet.pdf \
  --query-variant "c.2216G>A" \
  --output samples/expected_output_11359211.json
```

### C. Expose the Paper as an MCP Server (`--serve-mcp`)

Launch the paper agent as a standard Model Context Protocol (`FastMCP`) stdio server so Claude Desktop, Cursor, or downstream clinical interpretation agents can call its tools:

```bash
python paper_to_gdvp_agent.py --pmid 11359211 --serve-mcp
```

Available MCP Tools:
- `query_variant_evidence(variant_query: str)`: Search by cDNA (`c.2216G>A`), protein change (`p.Arg739Gln`), or gene symbol (`SCN1A`).
- `match_patient_phenotypes(patient_hpo_ids: list[str])`: Compare a patient's HPO profile (`["HP:0002069", "HP:0032894"]`) against probands reported in the paper (`ACMG PP4`).
- `evaluate_acmg_criteria(assertion_id: str | None)`: Audit all ACMG evidence tags (`PVS1`, `PS2`, `PS3`, `PM1`) and verify sentence-level provenance.

---

## 5. Sample Output (`query_variant_evidence("c.2216G>A")`)

```json
[
  {
    "assertion_id": "ASN-002",
    "pmid": "11359211",
    "section": "Case_Report",
    "gene_symbol": "SCN1A",
    "variant": {
      "cdna_change": "c.2216G>A",
      "protein_change": "p.Arg739Gln",
      "transcript": "NM_001165963.4",
      "zygosity": "heterozygous",
      "origin": "de_novo",
      "functional_domain": "S4 transmembrane voltage-sensor segment of domain II"
    },
    "disease_name": "Dravet syndrome",
    "phenotypes": [
      "febrile status epilepticus",
      "generalized tonic-clonic seizures",
      "moderate cognitive impairment"
    ],
    "proband_count": 1,
    "functional_assay_result": "Whole-cell patch-clamp recordings in HEK293 cells expressing mutant SCN1A p.Arg739Gln demonstrated complete loss of functional sodium current density compared to wild-type NaV1.1 channels.",
    "acmg_tags": [
      {
        "code": "PS2",
        "justification": "Confirmed de novo heterozygous variant; neither parent carried the c.2216G>A alteration and paternity was confirmed."
      },
      {
        "code": "PM1",
        "justification": "Located within the highly conserved S4 transmembrane voltage-sensor segment of domain II."
      },
      {
        "code": "PS3",
        "justification": "Whole-cell patch-clamp recordings in HEK293 cells demonstrated complete loss of functional sodium current density."
      }
    ],
    "verbatim_quote": "In Patient SMEI-2, direct sequencing revealed a de novo heterozygous missense substitution c.2216G>A (p.Arg739Gln) located within the highly conserved S4 transmembrane voltage-sensor segment of domain II.",
    "grounded_gene": {
      "raw_text": "SCN1A",
      "canonical_id": "HGNC:10585",
      "label": "sodium voltage-gated channel alpha subunit 1"
    },
    "grounded_disease": {
      "raw_text": "Dravet syndrome",
      "canonical_id": "MONDO:0011073",
      "label": "Dravet syndrome"
    },
    "grounded_phenotypes": [
      {
        "raw_text": "febrile status epilepticus",
        "canonical_id": "HP:0032894",
        "label": "Febrile status epilepticus"
      },
      {
        "raw_text": "generalized tonic-clonic seizures",
        "canonical_id": "HP:0002069",
        "label": "Bilateral tonic-clonic seizure"
      },
      {
        "raw_text": "moderate cognitive impairment",
        "canonical_id": "HP:0002342",
        "label": "Intellectual disability, moderate"
      }
    ],
    "quote_verified": true
  }
]
```

---

## 6. Running Tests

```bash
pytest -v
```
