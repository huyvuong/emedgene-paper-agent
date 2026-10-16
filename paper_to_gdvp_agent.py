#!/usr/bin/env python3
"""
Emedgene-Style Clinical Literature NLP Extraction & Grounding Agent Prototype
=============================================================================
Extracts Gene-Disease-Variant-Phenotype (GDVP) assertions with verbatim sentence
provenance from peer-reviewed articles (via PubMed ID or local PDF), grounds
entities deterministically against live EBI OLS4 (HPO, MONDO) and MyGene.info (HGNC),
and exposes the curated paper state as a callable FastMCP tool server.

Usage:
  python paper_to_gdvp_agent.py
  python paper_to_gdvp_agent.py --pmid 11359211
  python paper_to_gdvp_agent.py --pdf samples/PMID_11359211_SCN1A_Dravet.pdf
  python paper_to_gdvp_agent.py --pdf samples/PMID_11359211_SCN1A_Dravet.pdf --output samples/expected_output_11359211.json
  python paper_to_gdvp_agent.py --serve-mcp
"""

# ruff: noqa: E402
import sys
from pathlib import Path

# Ensure `src/` is on sys.path when invoked directly from repository root
_SRC_DIR = Path(__file__).resolve().parent / "src"
if _SRC_DIR.exists() and str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from emedgene_agent.cli import main, run_pipeline, run_prototype_demo
from emedgene_agent.extractor import (
    EXTRACTION_SYSTEM_PROMPT,
    extract_gdvp_from_article,
)
from emedgene_agent.grounder import BiomedicalGrounder
from emedgene_agent.mcp_server import (
    evaluate_acmg_criteria,
    match_patient_phenotypes,
    mcp,
    query_variant_evidence,
)
from emedgene_agent.parser import (
    SAMPLE_ARTICLE_PMID,
    SAMPLE_ARTICLE_TEXT,
    SAMPLE_ARTICLE_TITLE,
    fetch_pubmed_article,
    parse_pdf_article,
)
from emedgene_agent.schemas import (
    ACMGEvidenceTag,
    GDVPAssertion,
    GroundedEntity,
    PaperKnowledgeBase,
    VariantMention,
)

__all__ = [
    "EXTRACTION_SYSTEM_PROMPT",
    "SAMPLE_ARTICLE_PMID",
    "SAMPLE_ARTICLE_TEXT",
    "SAMPLE_ARTICLE_TITLE",
    "ACMGEvidenceTag",
    "BiomedicalGrounder",
    "GDVPAssertion",
    "GroundedEntity",
    "PaperKnowledgeBase",
    "VariantMention",
    "evaluate_acmg_criteria",
    "extract_gdvp_from_article",
    "fetch_pubmed_article",
    "main",
    "match_patient_phenotypes",
    "mcp",
    "parse_pdf_article",
    "query_variant_evidence",
    "run_pipeline",
    "run_prototype_demo",
]

if __name__ == "__main__":
    main()
