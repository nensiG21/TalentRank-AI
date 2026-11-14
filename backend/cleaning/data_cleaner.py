
import json
import re
from pathlib import Path


# Project directories
BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "processed" / "extracted_resumes.json"

OUTPUT_FILE = BASE_DIR / "data" / "processed" / "cleaned_resumes.json"


def clean_text(text):
    """
    Clean extracted resume text without removing
    meaningful candidate information.
    """

    if not isinstance(text, str):
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove unnecessary tabs and repeated spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_resume(resume):
    """
    Clean one resume and identify missing information.
    """

    original_text = resume.get("extracted_text", "")

    cleaned_text = clean_text(original_text)

    status = resume.get("status", "unknown")

    # Identify missing information
    missing_fields = []

    if not cleaned_text:
        missing_fields.append("resume_content")

    return {
        "filename": resume.get("filename", "unknown"),
        "extraction_status": status,
        "cleaning_status": "success" if cleaned_text else "empty",
        "cleaned_text": cleaned_text,
        "missing_fields": missing_fields
    }


def clean_all_resumes():

    # Read extracted resume data
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        resumes = json.load(file)

    cleaned_resumes = []

    for resume in resumes:

        cleaned_resume = process_resume(resume)

        cleaned_resumes.append(cleaned_resume)

        print(
            f"{cleaned_resume['filename']}: "
            f"{cleaned_resume['cleaning_status']}"
        )

    # Save cleaned data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            cleaned_resumes,
            file,
            indent=4,
            ensure_ascii=False
        )

    successful = sum(
        r["cleaning_status"] == "success"
        for r in cleaned_resumes
    )

    empty = sum(
        r["cleaning_status"] == "empty"
        for r in cleaned_resumes
    )

    print("\n----- DATA CLEANING SUMMARY -----")
    print(f"Total resumes: {len(cleaned_resumes)}")
    print(f"Successfully cleaned: {successful}")
    print(f"Empty resumes: {empty}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    clean_all_resumes()
