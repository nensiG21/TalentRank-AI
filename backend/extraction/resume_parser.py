    
from pathlib import Path
from docx import Document
import json

# Project directories
BASE_DIR = Path(__file__).resolve().parents[1]

RESUME_DIR = BASE_DIR / "data" / "raw_resumes"
OUTPUT_DIR = BASE_DIR / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_docx_text(file_path):
    """Extract text from paragraphs and tables in a DOCX file."""

    try:
        document = Document(file_path)

        extracted_text = []

        # Extract paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()

            if text:
                extracted_text.append(text)

        # Extract tables
        for table in document.tables:
            for row in table.rows:
                row_text = [
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                ]

                if row_text:
                    extracted_text.append(" | ".join(row_text))

        return "\n".join(extracted_text)

    except Exception as error:
        raise RuntimeError(f"Could not read document: {error}")


def process_resumes():

    results = []

    resume_files = sorted(RESUME_DIR.glob("*.docx"))

    print(f"Found {len(resume_files)} DOCX resumes.")

    for resume_file in resume_files:

        try:
            text = extract_docx_text(resume_file)

            status = "success" if text.strip() else "empty"

            results.append({
                "filename": resume_file.name,
                "status": status,
                "extracted_text": text
            })

            print(f"{resume_file.name}: {status}")

        except Exception as error:

            results.append({
                "filename": resume_file.name,
                "status": "error",
                "extracted_text": "",
                "error": str(error)
            })

            print(f"{resume_file.name}: ERROR - {error}")

    # Save extracted data
    output_file = OUTPUT_DIR / "extracted_resumes.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4, ensure_ascii=False)

    successful = sum(r["status"] == "success" for r in results)
    empty = sum(r["status"] == "empty" for r in results)
    errors = sum(r["status"] == "error" for r in results)

    print("\n----- EXTRACTION SUMMARY -----")
    print(f"Total resumes: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Empty: {empty}")
    print(f"Errors: {errors}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    process_resumes()
