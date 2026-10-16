"""FastMCP Server exposing an extracted and grounded peer-reviewed paper as a callable Clinical Genomics Agent."""

import json

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from emedgene_agent.schemas import PaperKnowledgeBase

mcp = FastMCP("PaperAgent_PMID_11359211")
PAPER_KB: PaperKnowledgeBase | None = None


def set_paper_kb(kb: PaperKnowledgeBase) -> None:
    """Set the active PaperKnowledgeBase served by the MCP agent."""
    global PAPER_KB
    PAPER_KB = kb


def get_paper_kb() -> PaperKnowledgeBase | None:
    """Retrieve the active PaperKnowledgeBase."""
    return PAPER_KB


@mcp.tool()
def query_variant_evidence(variant_query: str) -> str:
    """
    Search this paper's knowledge base by cDNA (e.g. 'c.2216G>A') or protein change ('p.Arg739Gln').
    Returns structured GDVP assertions, grounded HGNC/HPO/MONDO codes, ACMG criteria, and verified quotes.
    """
    if not PAPER_KB:
        return "Knowledge base not initialized."
    q = variant_query.strip().lower()
    matches = [
        a.model_dump()
        for a in PAPER_KB.assertions
        if (a.variant.cdna_change and q in a.variant.cdna_change.lower())
        or (a.variant.protein_change and q in a.variant.protein_change.lower())
        or (a.gene_symbol and q == a.gene_symbol.lower())
    ]
    return json.dumps(matches, indent=2)


@mcp.tool()
def match_patient_phenotypes(patient_hpo_ids: list[str]) -> str:
    """
    Compare a clinical proband's HPO IDs (e.g. ['HP:0002123', 'HP:0002069']) against cases in this paper.
    Returns matching variants and overlapping phenotype evidence (ACMG PP4 evaluation).
    """
    if not PAPER_KB:
        return "Knowledge base not initialized."
    patient_set = {hpo.strip().upper() for hpo in patient_hpo_ids}
    results = []
    for a in PAPER_KB.assertions:
        paper_hpos = {
            p.canonical_id
            for p in a.grounded_phenotypes
            if p.canonical_id and p.canonical_id != "UNRESOLVED"
        }
        overlap = sorted(patient_set.intersection(paper_hpos))
        results.append(
            {
                "assertion_id": a.assertion_id,
                "gene": a.gene_symbol,
                "grounded_gene_id": a.grounded_gene.canonical_id if a.grounded_gene else None,
                "variant": f"{a.variant.cdna_change} ({a.variant.protein_change})",
                "disease": (
                    f"{a.grounded_disease.label} ({a.grounded_disease.canonical_id})"
                    if a.grounded_disease and a.grounded_disease.canonical_id
                    else a.disease_name
                ),
                "overlapping_hpo_ids": overlap,
                "paper_hpo_ids": sorted(paper_hpos),
                "overlap_ratio": f"{len(overlap)}/{len(paper_hpos)}",
                "acmg_codes": [t.code for t in a.acmg_tags],
                "quote_verified": a.quote_verified,
            }
        )
    return json.dumps(results, indent=2)


@mcp.tool()
def evaluate_acmg_criteria(assertion_id: str | None = None) -> str:
    """
    Audit all ACMG/AMP evidence codes (PVS1, PS2, PS3, PM1, etc.) supported by this paper,
    including sentence-level verbatim provenance and quote verification status.
    """
    if not PAPER_KB:
        return "Knowledge base not initialized."
    records = []
    for a in PAPER_KB.assertions:
        if assertion_id and a.assertion_id.lower() != assertion_id.strip().lower():
            continue
        records.append(
            {
                "assertion_id": a.assertion_id,
                "pmid": a.pmid,
                "section": a.section,
                "gene": a.gene_symbol,
                "variant": f"{a.variant.cdna_change} ({a.variant.protein_change})",
                "acmg_tags": [t.model_dump() for t in a.acmg_tags],
                "functional_assay_result": a.functional_assay_result,
                "verbatim_quote": a.verbatim_quote,
                "quote_verified": a.quote_verified,
            }
        )
    return json.dumps(records, indent=2)
