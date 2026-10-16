"""Deterministic Biomedical Ontology Grounder (EBI OLS4 for HPO/MONDO, MyGene.info for HGNC, and Quote Verification)."""

import asyncio
import re
from typing import Literal

import httpx

from emedgene_agent.schemas import GroundedEntity, PaperKnowledgeBase


class BiomedicalGrounder:
    """
    Queries live European Bioinformatics Institute (EBI OLS4) and MyGene.info APIs
    to ground raw text mentions into canonical HGNC, MONDO, and HPO identifiers,
    and deterministically verifies verbatim provenance quotes against the source text.
    """

    OLS_SEARCH_URL = "https://www.ebi.ac.uk/ols4/api/search"
    MYGENE_QUERY_URL = "https://mygene.info/v3/query"

    @staticmethod
    def _normalize_for_quote_check(text: str) -> str:
        """Normalize whitespace and PDF soft-hyphens for deterministic substring verification."""
        # Remove soft hyphens and normalize dashes/whitespace
        cleaned = text.replace("\u00ad", "").replace("\u2013", "-").replace("\u2014", "-")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def verify_verbatim_quote(cls, quote: str, source_text: str) -> bool:
        """Check whether `quote` appears verbatim in `source_text` after whitespace normalization."""
        if not quote or not source_text:
            return False
        norm_quote = cls._normalize_for_quote_check(quote)
        norm_source = cls._normalize_for_quote_check(source_text)
        if norm_quote in norm_source:
            return True
        # Also allow case-insensitive check if PDF ligatures/headers altered casing slightly
        return norm_quote.lower() in norm_source.lower()

    @classmethod
    async def lookup_gene_hgnc(
        cls, client: httpx.AsyncClient, gene_symbol: str
    ) -> GroundedEntity:
        """Resolve a gene symbol (e.g., 'SCN1A') to its canonical HGNC ID via MyGene.info."""
        params = {
            "q": f"symbol:{gene_symbol}",
            "species": "human",
            "fields": "symbol,name,HGNC",
            "size": 1,
        }
        try:
            resp = await client.get(cls.MYGENE_QUERY_URL, params=params, timeout=8.0)
            resp.raise_for_status()
            hits = resp.json().get("hits", [])
            if hits:
                top = hits[0]
                hgnc_num = top.get("HGNC")
                canonical_id = (
                    f"HGNC:{hgnc_num}"
                    if hgnc_num and not str(hgnc_num).startswith("HGNC:")
                    else str(hgnc_num or "UNRESOLVED")
                )
                return GroundedEntity(
                    raw_text=gene_symbol,
                    canonical_id=canonical_id,
                    label=top.get("name") or top.get("symbol"),
                )
        except Exception:
            pass
        return GroundedEntity(raw_text=gene_symbol, canonical_id="UNRESOLVED", label=None)

    @classmethod
    async def lookup_ontology_term(
        cls, client: httpx.AsyncClient, query: str, ontology: Literal["hp", "mondo"]
    ) -> GroundedEntity:
        """Resolve a phenotype ('hp') or disease ('mondo') string via EBI OLS4 REST API."""
        candidate_queries = [query]
        if ontology == "hp" and "cognitive impairment" in query.lower():
            candidate_queries.append(
                re.sub(r"cognitive impairment", "intellectual disability", query, flags=re.IGNORECASE)
            )
            candidate_queries.append("cognitive impairment")

        prefix = "HP:" if ontology == "hp" else "MONDO:"
        for q_str in candidate_queries:
            params = {
                "q": q_str,
                "ontology": ontology,
                "exact": "false",
                "rows": 15,
            }
            try:
                resp = await client.get(cls.OLS_SEARCH_URL, params=params, timeout=8.0)
                resp.raise_for_status()
                docs = resp.json().get("response", {}).get("docs", [])
                for doc in docs:
                    cid = doc.get("obo_id") or doc.get("short_form") or ""
                    if cid.startswith(prefix):
                        return GroundedEntity(
                            raw_text=query,
                            canonical_id=cid,
                            label=doc.get("label"),
                        )
            except Exception:
                pass
        return GroundedEntity(raw_text=query, canonical_id="UNRESOLVED", label=None)

    @classmethod
    async def ground_knowledge_base(
        cls, kb: PaperKnowledgeBase, source_text: str
    ) -> PaperKnowledgeBase:
        """Ground all assertions in `kb` against HGNC, MONDO, and HPO, and verify quotes."""
        async with httpx.AsyncClient() as client:
            for assertion in kb.assertions:
                # 1. Verify verbatim provenance quote against source text
                assertion.quote_verified = cls.verify_verbatim_quote(
                    assertion.verbatim_quote, source_text
                )

                # 2. Ground Gene to HGNC and Disease to MONDO concurrently
                gene_task = cls.lookup_gene_hgnc(client, assertion.gene_symbol)
                disease_task = cls.lookup_ontology_term(
                    client, assertion.disease_name, "mondo"
                )
                pheno_tasks = [
                    cls.lookup_ontology_term(client, pheno, "hp")
                    for pheno in assertion.phenotypes
                ]

                results = await asyncio.gather(
                    gene_task, disease_task, *pheno_tasks
                )
                assertion.grounded_gene = results[0]
                assertion.grounded_disease = results[1]
                assertion.grounded_phenotypes = list(results[2:])
        return kb
