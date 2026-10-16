"""Strict Pydantic Data Contracts for Emedgene-Style GDVP Clinical Assertions."""

from typing import Literal

from pydantic import BaseModel, Field


class GroundedEntity(BaseModel):
    """Canonical ontology resolution for a raw text biomedical mention."""

    raw_text: str = Field(description="Exact entity string as written in the article.")
    canonical_id: str | None = Field(
        default=None,
        description="Resolved ontology ID (HGNC, HPO, MONDO, HGVS, or UNRESOLVED).",
    )
    label: str | None = Field(
        default=None,
        description="Official ontology term label from HGNC, OLS4 (HPO/MONDO), or Ensembl.",
    )


class PubTatorEntity(BaseModel):
    """Pre-annotated biomedical entity span from NCBI PubTator3 NER."""

    text: str = Field(description="Surface mention in article text.")
    entity_type: str = Field(description="Entity class (Gene, Mutation, Disease, Chemical, Species).")
    identifier: str | None = Field(default=None, description="Normalized NCBI/MeSH/tmVar identifier.")
    section: str | None = Field(default=None, description="Section where the entity was annotated.")


class VariantMention(BaseModel):
    """Structured representation of a genetic variant reported in clinical literature."""

    cdna_change: str | None = Field(
        default=None, description="cDNA HGVS notation if present, e.g., c.2216G>A"
    )
    protein_change: str | None = Field(
        default=None, description="Protein HGVS notation if present, e.g., p.Arg739Gln"
    )
    transcript: str | None = Field(
        default=None, description="RefSeq transcript if mentioned, e.g., NM_001165963.4"
    )
    zygosity: Literal[
        "heterozygous", "homozygous", "hemizygous", "compound_heterozygous", "unknown"
    ] = "unknown"
    origin: Literal[
        "de_novo", "maternal", "paternal", "inherited_unspecified", "somatic", "unknown"
    ] = "unknown"
    functional_domain: str | None = Field(
        default=None,
        description="Protein domain mentioned, e.g., S4 voltage-sensor domain",
    )


class ACMGEvidenceTag(BaseModel):
    """Explainable ACMG/AMP variant interpretation criteria tag with justification."""

    code: Literal[
        "PVS1",
        "PS1",
        "PS2",
        "PS3",
        "PS4",
        "PM1",
        "PM2",
        "PM4",
        "PM5",
        "PP1",
        "PP2",
        "PP3",
        "PP4",
        "BA1",
        "BS1",
        "BS2",
        "BS3",
        "BP4",
    ]
    justification: str = Field(
        description="Why this paper supports this ACMG/AMP evidence code."
    )


class GDVPAssertion(BaseModel):
    """Gene-Disease-Variant-Phenotype (GDVP) explainable assertion with sentence-level provenance."""

    assertion_id: str = Field(description="Unique identifier, e.g., ASN-001")
    pmid: str = Field(description="PubMed ID of the source article.")
    section: Literal[
        "Abstract", "Introduction", "Methods", "Results", "Case_Report", "Table", "Functional_Assay", "Discussion"
    ]
    gene_symbol: str = Field(description="Official HGNC gene symbol, e.g., SCN1A")
    variant: VariantMention
    disease_name: str = Field(
        description="Reported condition or syndrome, e.g., Dravet syndrome"
    )
    phenotypes: list[str] = Field(
        description="List of specific clinical signs/symptoms reported for this carrier."
    )
    proband_count: int = Field(
        description="Number of unrelated affected probands carrying this variant in the paper."
    )
    functional_assay_result: str | None = Field(
        default=None,
        description="Summary of wet-lab functional validation if performed (e.g., patch-clamp showing loss of function).",
    )
    acmg_tags: list[ACMGEvidenceTag]
    verbatim_quote: str = Field(
        description="Exact, word-for-word sentence from the source text supporting this assertion."
    )
    # Populated post-extraction by deterministic Ontology Grounder
    grounded_gene: GroundedEntity | None = None
    grounded_disease: GroundedEntity | None = None
    grounded_phenotypes: list[GroundedEntity] = Field(default_factory=list)
    quote_verified: bool = False


class PaperKnowledgeBase(BaseModel):
    """Complete structured knowledge base extracted from a peer-reviewed article."""

    pmid: str
    title: str
    source_type: str = Field(
        default="curated_excerpt",
        description="Origin of the parsed text (e.g., 'pdf', 'pubtator3_bioc', 'pubmed_xml', 'curated_excerpt').",
    )
    pubtator_entities: list[PubTatorEntity] = Field(
        default_factory=list,
        description="Candidate biomedical entities pre-extracted via NCBI PubTator3 API.",
    )
    assertions: list[GDVPAssertion]
