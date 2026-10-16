"""End-to-end tests for PDF parsing, GDVP extraction, live ontology grounding, and FastMCP tools."""

import json
from pathlib import Path

import pytest

from emedgene_agent.cli import run_pipeline
from emedgene_agent.grounder import BiomedicalGrounder
from emedgene_agent.mcp_server import (
    evaluate_acmg_criteria,
    match_patient_phenotypes,
    query_variant_evidence,
)
from emedgene_agent.parser import SAMPLE_ARTICLE_TEXT, parse_pdf_article
from emedgene_agent.pdf_generator import create_sample_clinical_pdf


def test_quote_verification():
    quote = (
        "In Patient SMEI-2, direct sequencing revealed a de novo heterozygous missense "
        "substitution c.2216G>A (p.Arg739Gln) located within the highly conserved S4 "
        "transmembrane voltage-sensor segment of domain II."
    )
    assert BiomedicalGrounder.verify_verbatim_quote(quote, SAMPLE_ARTICLE_TEXT) is True
    assert (
        BiomedicalGrounder.verify_verbatim_quote(
            "This fabricated sentence does not exist in the paper.", SAMPLE_ARTICLE_TEXT
        )
        is False
    )


def test_pdf_generation_and_parsing(tmp_path: Path):
    pdf_file = create_sample_clinical_pdf(tmp_path / "PMID_11359211_SCN1A_Dravet.pdf")
    assert pdf_file.exists()

    parsed = parse_pdf_article(pdf_file)
    assert parsed.pmid == "11359211"
    assert "SCN1A" in parsed.text
    assert "c.2216G>A" in parsed.text
    assert "[SECTION:" in parsed.text


@pytest.mark.asyncio
async def test_end_to_end_pmid_pipeline_and_mcp_tools():
    kb = await run_pipeline(pmid="11359211")
    assert kb.pmid == "11359211"
    assert len(kb.assertions) >= 2

    # Check quote verification and ontology grounding
    asn2 = next(a for a in kb.assertions if a.variant.cdna_change == "c.2216G>A")
    assert asn2.quote_verified is True
    assert asn2.grounded_gene is not None
    assert asn2.grounded_gene.canonical_id in ("HGNC:10585", "UNRESOLVED")
    assert asn2.grounded_disease is not None
    assert (
        asn2.grounded_disease.canonical_id.startswith("MONDO:")
        or asn2.grounded_disease.canonical_id == "UNRESOLVED"
    )

    # Test MCP Tool 1: query_variant_evidence
    raw_matches = query_variant_evidence("c.2216G>A")
    matches = json.loads(raw_matches)
    assert len(matches) == 1
    assert matches[0]["variant"]["protein_change"] == "p.Arg739Gln"
    assert matches[0]["quote_verified"] is True

    # Test MCP Tool 2: match_patient_phenotypes
    raw_overlap = match_patient_phenotypes(["HP:0032656", "HP:0025190"])
    overlap_data = json.loads(raw_overlap)
    assert len(overlap_data) >= 2

    # Test MCP Tool 3: evaluate_acmg_criteria
    raw_acmg = evaluate_acmg_criteria("ASN-002")
    acmg_data = json.loads(raw_acmg)
    assert len(acmg_data) == 1
    codes = [t["code"] for t in acmg_data[0]["acmg_tags"]]
    assert "PS2" in codes
    assert "PS3" in codes
