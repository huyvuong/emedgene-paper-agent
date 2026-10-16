"""CLI helper script to generate the sample clinical genetics PDF article."""

from pathlib import Path

from emedgene_agent.pdf_generator import create_sample_clinical_pdf

if __name__ == "__main__":
    out = create_sample_clinical_pdf(
        Path(__file__).resolve().parent.parent / "samples" / "PMID_11359211_SCN1A_Dravet.pdf"
    )
    print(f"Generated sample clinical PDF: {out}")
