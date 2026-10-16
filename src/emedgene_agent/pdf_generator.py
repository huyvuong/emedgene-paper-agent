"""Generate a realistic peer-reviewed clinical genetics PDF article for testing PDF NLP extraction."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_sample_clinical_pdf(output_path: str | Path) -> Path:
    """Create the sample SCN1A Dravet syndrome clinical report PDF at `output_path`."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title="De Novo Mutations in the Sodium-Channel Gene SCN1A Cause Severe Myoclonic Epilepsy of Infancy",
        author="Claes et al. (Representative Clinical Excerpt, PMID: 11359211)",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "JournalTitle",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "JournalMeta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#444444"),
        spaceAfter=12,
    )
    sec_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#1a365d"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )

    story = []

    story.append(
        Paragraph(
            "De Novo Mutations in the Sodium-Channel Gene SCN1A Cause Severe Myoclonic Epilepsy of Infancy",
            title_style,
        )
    )
    story.append(
        Paragraph(
            "PMID: 11359211 | American Journal of Human Genetics | Clinical Case Report & Functional Characterization Excerpt",
            meta_style,
        )
    )

    story.append(Paragraph("Abstract", sec_style))
    story.append(
        Paragraph(
            "Severe myoclonic epilepsy of infancy (SMEI), or Dravet syndrome, is a rare disorder characterized by "
            "generalized tonic, clonic, and tonic-clonic seizures that are initially induced by fever and begin during "
            "the first year of life. Later, patients also manifest other seizure types, including absence, myoclonic, "
            "and simple and complex partial seizures, accompanied by psychomotor delay and ataxia.",
            body_style,
        )
    )

    story.append(Paragraph("Results / Case_Report", sec_style))
    story.append(
        Paragraph(
            "We screened the SCN1A gene (NM_001165963.4) in 7 unrelated probands diagnosed with Dravet syndrome. "
            "In Patient SMEI-1, we identified a de novo heterozygous nonsense mutation c.3733C>T (p.Arg1245Ter) in exon 19. "
            "Both parents tested negative for the variant, and paternity was genetically confirmed. Patient SMEI-1 presented "
            "at 5 months of age with prolonged hemiclonic febrile seizures, subsequently developing intractable myoclonic seizures, "
            "ataxia, and severe intellectual disability by age 3.",
            body_style,
        )
    )
    story.append(
        Paragraph(
            "In Patient SMEI-2, direct sequencing revealed a de novo heterozygous missense substitution c.2216G>A (p.Arg739Gln) "
            "located within the highly conserved S4 transmembrane voltage-sensor segment of domain II. Neither parent carried "
            "the c.2216G>A alteration (paternity confirmed). Patient SMEI-2 exhibited febrile status epilepticus at 6 months, "
            "followed by generalized tonic-clonic seizures and moderate cognitive impairment.",
            body_style,
        )
    )

    story.append(Paragraph("Table 1. Summary of SCN1A Variants and Clinical Phenotypes", sec_style))
    table_data = [
        ["Patient", "Gene", "Transcript", "cDNA", "Protein", "Origin", "Zygosity", "Phenotypes"],
        [
            "SMEI-1",
            "SCN1A",
            "NM_001165963.4",
            "c.3733C>T",
            "p.Arg1245Ter",
            "de_novo",
            "heterozygous",
            "Febrile seizures, myoclonic seizures, ataxia, severe ID",
        ],
        [
            "SMEI-2",
            "SCN1A",
            "NM_001165963.4",
            "c.2216G>A",
            "p.Arg739Gln",
            "de_novo",
            "heterozygous",
            "Febrile status epilepticus, GTCS, moderate cognitive impairment",
        ],
    ]
    tbl = Table(table_data, colWidths=[45, 42, 78, 55, 65, 45, 65, 115])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Functional_Assay", sec_style))
    story.append(
        Paragraph(
            "Whole-cell patch-clamp recordings in HEK293 cells expressing the mutant SCN1A p.Arg739Gln channel demonstrated "
            "a complete loss of functional sodium current density compared to wild-type NaV1.1 channels, confirming a "
            "deleterious loss-of-function mechanism.",
            body_style,
        )
    )

    doc.build(story)
    return path
