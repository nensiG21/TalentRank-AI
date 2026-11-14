from pathlib import Path
import json
import re
import uuid
import os
import shutil

import pymupdf
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from cleaning.data_cleaner import process_resume
from extraction.resume_parser import extract_docx_text
from extraction.candidate_extractor import extract_candidate
from matching.classifier import (
    get_candidate_sections,
    calculate_role_score,
    classify_candidate,
    get_lca_project_evidence,
    get_experience_review,
)
from matching.ranking import rank_candidates
from matching.duplicate_detector import detect_duplicates

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_RESUME_DIR = DATA_DIR / "raw_resumes"
DEMO_DATA_DIR = BASE_DIR / "demo_data"

DEMO_FILES = [
    "extracted_resumes.json",
    "cleaned_resumes.json",
    "candidate_profiles.json",
    "candidate_classifications.json",
    "ranked_candidates.json",
]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per file
MAX_FILES_PER_UPLOAD = 20
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

app = FastAPI(
    title="TalentRank-AI API",
    description="AI-powered resume classification and ranking API",
    version="1.1.0",
)
@app.on_event("startup")
def startup_event():
    initialize_demo_data()

def initialize_demo_data():
    """
    Load fictional demo data on Render when enabled.
    Never overwrites existing processed data.
    """
    if os.getenv("USE_DEMO_DATA", "").lower() != "true":
        return

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    for filename in DEMO_FILES:
        source = DEMO_DATA_DIR / filename
        destination = PROCESSED_DIR / filename

        if not source.exists():
            raise FileNotFoundError(
                f"Demo data file missing: {source}"
            )

        if not destination.exists():
            shutil.copy2(source, destination)
            print(f"Loaded demo dataset: {filename}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://talent-rank-ai-sable.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json(filename):
    file_path = PROCESSED_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{filename} not found. Run the processing pipeline first.",
        )
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename, data):
    """Write JSON safely so an interrupted write does not truncate the old file."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    destination = PROCESSED_DIR / filename
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    temporary.replace(destination)


def extract_pdf_text(file_path):
    """Extract selectable text from every page of a PDF resume."""
    try:
        with pymupdf.open(file_path) as document:
            return "\n".join(page.get_text("text") for page in document).strip()
    except Exception as error:
        raise RuntimeError(f"Could not read PDF: {error}") from error


def extract_resume_text(file_path):
    extension = file_path.suffix.lower()
    if extension == ".docx":
        return extract_docx_text(file_path)
    if extension == ".pdf":
        return extract_pdf_text(file_path)
    raise ValueError("Only PDF and DOCX files are supported.")


def classify_profile(profile):
    """Run the same role-scoring and classification logic used by the batch pipeline."""
    sections = get_candidate_sections(profile)
    lca_result = calculate_role_score(sections, "lca")
    uiux_result = calculate_role_score(sections, "ui_ux")

    category, reason, lca_qualified, uiux_qualified = classify_candidate(
        lca_result, uiux_result, sections
    )

    return {
        "filename": profile.get("filename", "Unknown"),
        "category": category,
        "classification_reason": reason,
        "lca": lca_result,
        "ui_ux": uiux_result,
        "lca_project_review": get_lca_project_evidence(sections),
        "experience_review": get_experience_review(sections),
        "manual_review_required": (
            lca_qualified
            or category == "Neither / Uncertain"
            or bool(profile.get("review_flags"))
            or bool(profile.get("missing_fields"))
            or bool(profile.get("review_required"))
        ),
        "role_evidence": {
            "lca_direct_evidence": lca_qualified,
            "ui_ux_direct_evidence": uiux_qualified,
        },
    }


def make_unique_filename(original_name):
    """Keep the extension but avoid overwriting any previously uploaded resume."""
    safe_name = Path(original_name or "resume").name
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    stem = Path(safe_name).stem[:80] or "resume"
    suffix = Path(safe_name).suffix.lower()
    return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"



def process_and_save_new_resumes(uploaded_records):
    """Process new resumes and detect duplicates across all candidates."""

    extracted = load_json("extracted_resumes.json")
    cleaned = load_json("cleaned_resumes.json")
    profiles = load_json("candidate_profiles.json")

    new_cleaned = [process_resume(record) for record in uploaded_records]
    new_profiles = [extract_candidate(record) for record in new_cleaned]
    new_classifications = [
        classify_profile(profile) for profile in new_profiles
    ]

    # Append new records to the existing datasets.
    extracted.extend(uploaded_records)
    cleaned.extend(new_cleaned)
    profiles.extend(new_profiles)

    existing_classifications = load_json(
        "candidate_classifications.json"
    )
    classifications = existing_classifications + new_classifications

    # Verify that profile and classification records are aligned.
    if len(profiles) != len(classifications):
        raise ValueError(
            "Candidate profiles and classifications have different counts."
        )

    # Recheck every candidate, including newly uploaded resumes.
    duplicate_info = detect_duplicates(profiles)

    for profile, candidate, duplicate in zip(
        profiles, classifications, duplicate_info
    ):
        profile.update(duplicate)
        candidate.update(duplicate)

        if duplicate["duplicate_review_required"]:
            candidate["manual_review_required"] = True

    duplicate_count = sum(
        1 for item in duplicate_info
        if item["duplicate_status"] == "duplicate"
    )

    duplicate_groups = len({
        item["duplicate_group_id"]
        for item in duplicate_info
        if item["duplicate_group_id"]
    })

    # Generate rankings after duplicate detection.
    lca_ranking = rank_candidates(classifications, "lca")
    uiux_ranking = rank_candidates(classifications, "ui_ux")

    rankings = {
        "total_candidates": len(classifications),
        "unique_candidates": len(classifications) - duplicate_count,
        "duplicate_records_excluded": duplicate_count,
        "duplicate_groups": duplicate_groups,
        "ranking_method": (
            "Candidates are ranked by preliminary role match score. "
            "Likely duplicate records are retained for HR review but "
            "excluded from role rankings. Scores are evidence-based "
            "prototype estimates, not validated hiring assessments."
        ),
        "lca_ranking": lca_ranking,
        "ui_ux_ranking": uiux_ranking,
    }

    # Save the complete updated datasets.
    save_json("extracted_resumes.json", extracted)
    save_json("cleaned_resumes.json", cleaned)
    save_json("candidate_profiles.json", profiles)
    save_json("candidate_classifications.json", classifications)
    save_json("ranked_candidates.json", rankings)

    return new_profiles, new_classifications, rankings



@app.get("/")
def home():
    return {"message": "TalentRank-AI API is running"}


@app.get("/api/health")
def health():
    return {"status": "healthy"}


@app.get("/api/classifications")
def get_classifications():
    return load_json("candidate_classifications.json")


@app.get("/api/rankings")
def get_rankings():
    return load_json("ranked_candidates.json")


@app.get("/api/profiles")
def get_profiles():
    return load_json("candidate_profiles.json")


@app.post("/api/upload")
async def upload_resumes(files: list[UploadFile] = File(...)):
    """Upload, process, classify, and rank multiple PDF/DOCX resumes."""
    if not files:
        raise HTTPException(status_code=400, detail="Please select at least one resume.")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"You can upload at most {MAX_FILES_PER_UPLOAD} resumes at once.",
        )

    RAW_RESUME_DIR.mkdir(parents=True, exist_ok=True)
    uploaded_records = []
    results = []

    for upload in files:
        original_name = Path(upload.filename or "").name
        extension = Path(original_name).suffix.lower()

        if extension not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": original_name or "Unknown",
                "status": "rejected",
                "message": "Unsupported file type. Upload a PDF or DOCX file.",
            })
            continue

        content = await upload.read()
        if not content:
            results.append({
                "filename": original_name,
                "status": "rejected",
                "message": "The uploaded file is empty.",
            })
            continue
        if len(content) > MAX_FILE_SIZE:
            results.append({
                "filename": original_name,
                "status": "rejected",
                "message": "File exceeds the 10 MB size limit.",
            })
            continue

        stored_name = make_unique_filename(original_name)
        stored_path = RAW_RESUME_DIR / stored_name

        try:
            stored_path.write_bytes(content)
            text = extract_resume_text(stored_path)
            status = "success" if text.strip() else "empty"
            uploaded_records.append({
                "filename": stored_name,
                "status": status,
                "extracted_text": text,
            })
            results.append({
                "filename": original_name,
                "stored_filename": stored_name,
                "status": status,
                "message": "Resume uploaded and queued for screening." if text.strip()
                else "No selectable text was found. HR review is required.",
            })
        except Exception as error:
            stored_path.unlink(missing_ok=True)
            results.append({
                "filename": original_name,
                "status": "error",
                "message": str(error),
            })

    if not uploaded_records:
        return {
            "message": "No resumes were processed. Check the file types and contents.",
            "uploaded": 0,
            "results": results,
        }

    try:
        new_profiles, new_classifications, rankings = process_and_save_new_resumes(
            uploaded_records
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Resume files were received, but processing failed: {error}",
        ) from error

    return {
        "message": "Resume upload and screening completed.",
        "uploaded": len(uploaded_records),
        "new_candidates": len(new_profiles),
        "total_candidates": rankings["total_candidates"],
        "unique_candidates": rankings["unique_candidates"],
        "duplicate_records_excluded": rankings["duplicate_records_excluded"],
        "duplicate_groups": rankings["duplicate_groups"],
        "classification_counts": {
            category: sum(1 for item in new_classifications if item["category"] == category)
            for category in ["LCA", "UI/UX", "Both", "Neither / Uncertain"]
        },
        "results": results,
    }
# Fix Swagger UI file upload rendering
_original_openapi = app.openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = _original_openapi()

    upload_schema = schema["components"]["schemas"].get(
        "Body_upload_resumes_api_upload_post"
    )

    if upload_schema:
        file_items = (
            upload_schema.get("properties", {})
            .get("files", {})
            .get("items", {})
        )

        if file_items.get("contentMediaType") == "application/octet-stream":
            file_items.pop("contentMediaType", None)
            file_items["format"] = "binary"

    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi