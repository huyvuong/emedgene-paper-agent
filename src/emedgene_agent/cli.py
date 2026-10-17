"""Command-Line Interface for Emedgene-Style Clinical Literature Extraction & Grounding Agent."""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from emedgene_agent.extractor import extract_gdvp_from_article
from emedgene_agent.grounder import BiomedicalGrounder
from emedgene_agent.mcp_server import (
    evaluate_acmg_criteria,
    match_patient_phenotypes,
    mcp,
    query_variant_evidence,
    set_paper_kb,
)
from emedgene_agent.parser import (
    SAMPLE_ARTICLE_PMID,
    SAMPLE_ARTICLE_TEXT,
    SAMPLE_ARTICLE_TITLE,
    ParsedArticle,
    fetch_pubmed_article,
    parse_pdf_article,
)
from emedgene_agent.schemas import PaperKnowledgeBase


async def run_pipeline(
    pmid: str | None = None,
    pdf_path: str | None = None,
    model: str = "gemini-3.8-flash",
    output_json: str | None = None,
) -> PaperKnowledgeBase:
    """Execute the end-to-end Parse -> NLP Extract -> Ontology Ground pipeline."""
    # Step 1: Parse input source (PDF, live PubMed/PubTator3 PMID, or default real-world article)
    if pdf_path:
        print(f"[1/3] Parsing clinical PDF document: {pdf_path} ...")
        article = parse_pdf_article(pdf_path, default_pmid=pmid)
    elif pmid:
        print(f"[1/3] Fetching article & PubTator3 NER annotations for PMID:{pmid} ...")
        try:
            article = await fetch_pubmed_article(pmid)
        except Exception:
            if pmid == SAMPLE_ARTICLE_PMID:
                article = ParsedArticle(
                    pmid=SAMPLE_ARTICLE_PMID,
                    title=SAMPLE_ARTICLE_TITLE,
                    text=SAMPLE_ARTICLE_TEXT,
                    source_type="curated_excerpt",
                )
            else:
                raise
    else:
        print(f"[1/3] Loading real-world article PMID:{SAMPLE_ARTICLE_PMID} (PubTator3 + Case Report)...")
        try:
            article = await fetch_pubmed_article(SAMPLE_ARTICLE_PMID)
        except Exception:
            article = ParsedArticle(
                pmid=SAMPLE_ARTICLE_PMID,
                title=SAMPLE_ARTICLE_TITLE,
                text=SAMPLE_ARTICLE_TEXT,
                source_type="curated_excerpt",
            )

    if article.pubtator_entities:
        print(
            f"      -> Retrieved {len(article.pubtator_entities)} pre-annotated NER spans from NCBI PubTator3"
        )

    # Step 2: Extract structured GDVP assertions
    print(f"[2/3] Extracting structured GDVP assertions from PMID:{article.pmid} ({article.source_type})...")
    kb = extract_gdvp_from_article(
        pmid=article.pmid,
        title=article.title,
        text=article.text,
        model=model,
        source_type=article.source_type,
        pubtator_entities=article.pubtator_entities,
        use_fallback_if_no_key=True,
    )

    # Step 3: Ground entities against live EBI OLS4 (MONDO & HPO) + MyGene.info (HGNC) & verify quotes
    print("[3/3] Grounding entities via live EBI OLS4 (MONDO & HPO) + MyGene.info (HGNC) & verifying quotes...")
    grounded_kb = await BiomedicalGrounder.ground_knowledge_base(kb, article.text)
    set_paper_kb(grounded_kb)

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(grounded_kb.model_dump_json(indent=2), encoding="utf-8")
        print(f"      -> Saved grounded knowledge base to {out_path}")

    return grounded_kb


async def run_prototype_demo(
    pmid: str | None = None,
    pdf_path: str | None = None,
    variant_query: str = "c.2216G>A",
    patient_hpos: list[str] | None = None,
    output_json: str | None = None,
) -> PaperKnowledgeBase:
    """Run the prototype pipeline and showcase interactive MCP Agent tool calls."""
    kb = await run_pipeline(pmid=pmid, pdf_path=pdf_path, output_json=output_json)

    print("\nPaper Agent Ready! Testing Agent Tool Calls:\n")
    print(f"--- Tool Call: query_variant_evidence('{variant_query}') ---")
    print(query_variant_evidence(variant_query))

    hpos = patient_hpos or ["HP:0032656", "HP:0025190", "HP:0002373", "HP:0001251"]
    print(f"\n--- Tool Call: match_patient_phenotypes({hpos}) ---")
    print(match_patient_phenotypes(hpos))

    print("\n--- Tool Call: evaluate_acmg_criteria('ASN-001') ---")
    print(evaluate_acmg_criteria("ASN-001"))

    return kb


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emedgene-Style Clinical Literature NLP Extraction (GDVP), "
            "Deterministic Ontology Grounding (HGNC/HPO/MONDO), and FastMCP Server."
        )
    )
    parser.add_argument(
        "--pmid",
        type=str,
        default=None,
        help="PubMed ID to fetch from NCBI PubTator3 API (default: 11359211).",
    )
    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Path to a local peer-reviewed article PDF to parse and extract.",
    )
    parser.add_argument(
        "--query-variant",
        type=str,
        default="c.2216G>A",
        help="Variant query (cDNA or protein change) to test with query_variant_evidence tool.",
    )
    parser.add_argument(
        "--patient-hpos",
        nargs="+",
        default=["HP:0032656", "HP:0025190", "HP:0002373", "HP:0001251"],
        help="Patient HPO IDs to test phenotype overlap scoring.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save the full grounded PaperKnowledgeBase JSON.",
    )
    parser.add_argument(
        "--serve-mcp",
        action="store_true",
        help="After extracting and grounding the paper, start the FastMCP stdio server.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.serve_mcp:
        asyncio.run(
            run_pipeline(
                pmid=args.pmid,
                pdf_path=args.pdf,
                output_json=args.output,
            )
        )
        mcp.run()
    else:
        asyncio.run(
            run_prototype_demo(
                pmid=args.pmid,
                pdf_path=args.pdf,
                variant_query=args.query_variant,
                patient_hpos=args.patient_hpos,
                output_json=args.output,
            )
        )


if __name__ == "__main__":
    main(sys.argv[1:])
