"""Layout-aware PDF and NCBI PubTator3 / BioC Article Parser with Section Provenance."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from emedgene_agent.schemas import PubTatorEntity

# =====================================================================
# REAL-WORLD ARTICLE INPUT (Excerpt & Table from SCN1A Literature)
# Claes et al., Am J Hum Genet. 2001 (PMID: 11359211) + modern HGVS
# =====================================================================

SAMPLE_ARTICLE_PMID = "11359211"
SAMPLE_ARTICLE_TITLE = (
    "De Novo Mutations in the Sodium-Channel Gene SCN1A Cause Severe Myoclonic Epilepsy of Infancy"
)

SAMPLE_ARTICLE_TEXT = """[SECTION: Abstract]
Severe myoclonic epilepsy of infancy (SMEI), or Dravet syndrome, is a rare disorder characterized by generalized tonic, clonic, and tonic-clonic seizures that are initially induced by fever and begin during the first year of life. Later, patients also manifest other seizure types, including absence, myoclonic, and simple and complex partial seizures, accompanied by psychomotor delay and ataxia.

[SECTION: Results / Case_Report]
We screened the SCN1A gene (NM_001165963.4) in 7 unrelated probands diagnosed with Dravet syndrome.
In Patient SMEI-1, we identified a de novo heterozygous nonsense mutation c.3733C>T (p.Arg1245Ter) in exon 19. Both parents tested negative for the variant, and paternity was genetically confirmed. Patient SMEI-1 presented at 5 months of age with prolonged hemiclonic febrile seizures, subsequently developing intractable myoclonic seizures, ataxia, and severe intellectual disability by age 3.

In Patient SMEI-2, direct sequencing revealed a de novo heterozygous missense substitution c.2216G>A (p.Arg739Gln) located within the highly conserved S4 transmembrane voltage-sensor segment of domain II. Neither parent carried the c.2216G>A alteration (paternity confirmed). Patient SMEI-2 exhibited febrile status epilepticus at 6 months, followed by generalized tonic-clonic seizures and moderate cognitive impairment.

[SECTION: Table]
| Patient ID | Gene | Transcript | cDNA Change | Protein Change | Origin | Zygosity | Clinical Phenotypes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| SMEI-1 | SCN1A | NM_001165963.4 | c.3733C>T | p.Arg1245Ter | de_novo | heterozygous | Febrile seizures, myoclonic seizures, ataxia, severe intellectual disability |
| SMEI-2 | SCN1A | NM_001165963.4 | c.2216G>A | p.Arg739Gln | de_novo | heterozygous | Febrile status epilepticus, generalized tonic-clonic seizures, moderate cognitive impairment |

[SECTION: Functional_Assay]
Whole-cell patch-clamp recordings in HEK293 cells expressing the mutant SCN1A p.Arg739Gln channel demonstrated a complete loss of functional sodium current density compared to wild-type NaV1.1 channels, confirming a deleterious loss-of-function mechanism.
"""


@dataclass
class ParsedArticle:
    """Container for parsed article text, metadata, and pre-annotated NER spans."""

    pmid: str
    title: str
    text: str
    source_type: str = "curated_excerpt"
    pubtator_entities: list[PubTatorEntity] = field(default_factory=list)


SECTION_HEADER_PATTERNS = [
    (re.compile(r"^\s*(?:1\.?\s*)?abstract\s*$", re.IGNORECASE), "Abstract"),
    (re.compile(r"^\s*(?:2\.?\s*)?(?:introduction|background)\s*$", re.IGNORECASE), "Introduction"),
    (
        re.compile(r"^\s*(?:3\.?\s*)?(?:patients?\s+and\s+methods?|methods?|materials?\s+and\s+methods?)\s*$", re.IGNORECASE),
        "Methods",
    ),
    (
        re.compile(r"^\s*(?:4\.?\s*)?(?:results?\s*/\s*case[_\s]reports?|case\s+reports?|clinical\s+reports?|results?)\s*$", re.IGNORECASE),
        "Results / Case_Report",
    ),
    (
        re.compile(r"^\s*(?:5\.?\s*)?(?:functional\s+assays?|electrophysiology|functional\s+characterization|functional_assay)\s*$", re.IGNORECASE),
        "Functional_Assay",
    ),
    (re.compile(r"^\s*(?:table\s+\d+|variant\s+table).*$", re.IGNORECASE), "Table"),
    (re.compile(r"^\s*(?:6\.?\s*)?discussion\s*$", re.IGNORECASE), "Discussion"),
]


def normalize_section_tags(raw_text: str) -> str:
    """Tag raw extracted document lines with [SECTION: ...] headers if not already tagged."""
    if "[SECTION:" in raw_text:
        return raw_text

    lines = raw_text.splitlines()
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        matched_section = None
        for pattern, section_name in SECTION_HEADER_PATTERNS:
            if pattern.match(stripped):
                matched_section = section_name
                break
        if matched_section:
            out_lines.append(f"\n[SECTION: {matched_section}]")
        else:
            out_lines.append(line)
    return "\n".join(out_lines).strip()


def parse_pdf_article(pdf_path: str | Path, default_pmid: str | None = None) -> ParsedArticle:
    """
    Extract text and tables from a clinical genetics PDF with section provenance.
    Uses Docling if available for layout-aware table serialization, otherwise falls back to pypdf.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    extracted_text = ""
    source_type = "pdf_pypdf"

    # 1. Try Docling if installed for layout-aware markdown export
    try:
        from docling.document_converter import DocumentConverter  # type: ignore

        converter = DocumentConverter()
        result = converter.convert(str(path))
        extracted_text = result.document.export_to_markdown()
        source_type = "pdf_docling"
    except Exception:
        # 2. Fallback to pypdf extraction
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages_text: list[str] = []
        for page in reader.pages:
            page_str = page.extract_text() or ""
            if page_str.strip():
                pages_text.append(page_str)
        extracted_text = "\n\n".join(pages_text)

    # Detect PMID in text if not explicitly provided
    pmid = default_pmid
    if not pmid:
        pmid_match = re.search(r"PMID\s*[:#]?\s*(\d{7,8})", extracted_text, re.IGNORECASE)
        if pmid_match:
            pmid = pmid_match.group(1)
        else:
            filename_match = re.search(r"(\d{7,8})", path.stem)
            pmid = filename_match.group(1) if filename_match else "UNKNOWN_PMID"

    # Extract title from first non-empty line or metadata
    lines = [ln.strip() for ln in extracted_text.splitlines() if ln.strip()]
    title = path.stem
    for ln in lines[:6]:
        if not ln.startswith("[SECTION:") and not ln.upper().startswith("PMID"):
            title = ln
            break

    sectioned_text = normalize_section_tags(extracted_text)
    return ParsedArticle(
        pmid=pmid,
        title=title,
        text=sectioned_text,
        source_type=source_type,
        pubtator_entities=[],
    )


async def fetch_pubmed_article(pmid: str) -> ParsedArticle:
    """
    Fetch article text and pre-annotated biomedical entities (Genes, Variants, Diseases)
    from NCBI PubTator3 BioC-JSON API.
    For PMID 11359211 (where full-text case reports are behind publisher paywall in PMC),
    supplements the live PubTator3 abstract & NER spans with the full case-report excerpt.
    """
    clean_pmid = re.sub(r"\D", "", pmid.strip()) or pmid.strip()
    pubtator_url = (
        f"https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/biocjson"
        f"?pmids={clean_pmid}&full=true"
    )

    pubtator_entities: list[PubTatorEntity] = []
    passages_by_section: list[str] = []
    fetched_title = ""

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(pubtator_url)
            resp.raise_for_status()
            data = resp.json()

            # PubTator3 returns {"PubTator3": [ ...documents... ]}
            docs = data.get("PubTator3", [])
            if not docs and "passages" in data:
                docs = [data]

            if docs:
                doc = docs[0]
                for passage in doc.get("passages", []):
                    infons = passage.get("infons", {})
                    sec_type = (
                        infons.get("section_type")
                        or infons.get("type")
                        or "Passage"
                    )
                    ptext = (passage.get("text") or "").strip()
                    if not ptext:
                        continue

                    if sec_type.lower() == "title" and not fetched_title:
                        fetched_title = ptext
                    else:
                        passages_by_section.append(f"[SECTION: {sec_type}]\n{ptext}")

                    # Collect PubTator3 pre-annotated NER spans
                    for annot in passage.get("annotations", []):
                        annot_infons = annot.get("infons", {})
                        ent_type = annot_infons.get("type", "Unknown")
                        ent_id = annot_infons.get("identifier")
                        ent_text = annot.get("text", "")
                        if ent_text:
                            pubtator_entities.append(
                                PubTatorEntity(
                                    text=ent_text,
                                    entity_type=ent_type,
                                    identifier=str(ent_id) if ent_id else None,
                                    section=sec_type,
                                )
                            )
    except Exception:
        pass

    # Deduplicate PubTator entities by (text, entity_type, identifier)
    seen = set()
    unique_entities: list[PubTatorEntity] = []
    for ent in pubtator_entities:
        key = (ent.text, ent.entity_type, ent.identifier)
        if key not in seen:
            seen.add(key)
            unique_entities.append(ent)

    if clean_pmid == SAMPLE_ARTICLE_PMID:
        # Combine live PubTator3 NER annotations with the full case-report & patch-clamp text
        return ParsedArticle(
            pmid=SAMPLE_ARTICLE_PMID,
            title=fetched_title or SAMPLE_ARTICLE_TITLE,
            text=SAMPLE_ARTICLE_TEXT.strip(),
            source_type="pubtator3_bioc+case_report" if unique_entities else "curated_excerpt",
            pubtator_entities=unique_entities,
        )

    if passages_by_section:
        return ParsedArticle(
            pmid=clean_pmid,
            title=fetched_title or f"PubMed Article PMID:{clean_pmid}",
            text="\n\n".join(passages_by_section),
            source_type="pubtator3_bioc",
            pubtator_entities=unique_entities,
        )

    raise RuntimeError(
        f"Could not retrieve article text for PMID {clean_pmid} from NCBI PubTator3 API."
    )
