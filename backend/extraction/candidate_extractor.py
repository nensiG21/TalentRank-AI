
import json
import re
from pathlib import Path


# --------------------------------------------------
# 1. FILE PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "processed" / "cleaned_resumes.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "candidate_profiles.json"


# --------------------------------------------------
# 2. CANONICAL SKILLS AND THEIR ALIASES
# --------------------------------------------------

SKILL_KEYWORDS = {
    "Python": ["Python"],
    "Java": ["Java"],
    "SQL": ["SQL"],
    "Excel": ["Excel", "MS Excel"],
    "Data Analysis": ["Data Analysis", "Data Analytics"],
    "Machine Learning": ["Machine Learning"],
    "Deep Learning": ["Deep Learning"],
    "Data Science": ["Data Science"],
    "Pandas": ["Pandas"],
    "NumPy": ["NumPy"],
    "Scikit-learn": ["Scikit-learn", "Scikit learn"],
    "Power BI": ["Power BI", "PowerBI"],
    "Tableau": ["Tableau"],

    "Figma": ["Figma"],
    "Adobe XD": ["Adobe XD"],
    "Photoshop": ["Photoshop"],
    "Illustrator": ["Illustrator"],
    "Wireframing": ["Wireframing", "Wireframes"],
    "Prototyping": ["Prototyping", "Prototypes"],
    "User Research": ["User Research", "User Interviews"],
    "Usability Testing": ["Usability Testing"],
    "UI/UX Design": ["UI/UX Design", "UX/UI Design", "UI UX"],

    "HTML": ["HTML"],
    "CSS": ["CSS"],
    "JavaScript": ["JavaScript"],
    "React": ["React.js", "React"],

    "Life Cycle Assessment": [
        "Life Cycle Assessment",
        "Life-Cycle Assessment",
        "LCA"
    ],
    "Life Cycle Inventory": [
        "Life Cycle Inventory",
        "Life-Cycle Inventory",
        "LCI"
    ],
    "SimaPro": ["SimaPro"],
    "GaBi": ["GaBi"],
    "OpenLCA": ["OpenLCA"],
    "ISO 14040/14044": ["ISO 14040", "ISO 14044"],
    "Sustainability": ["Sustainability"],
    "EPD": ["EPD", "Environmental Product Declaration"],
    "Carbon Accounting": ["Carbon Accounting"],
    "GHG Accounting": ["GHG Accounting"],
    "Environmental Impact Assessment": [
        "Environmental Impact Assessment",
        "EIA"
    ]
}


# --------------------------------------------------
# 3. SECTION HEADING VARIATIONS
# --------------------------------------------------

SECTION_ALIASES = {
    "education": [
        "education",
        "academic background",
        "educational qualifications",
        "educational qualification",
        "academic qualifications",
        "education details",
        "academic details"
    ],

    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship experience",
        "internships",
        "work history",
        "professional background"
    ],

    "projects": [
        "projects",
        "project",
        "projects deliverables",
        "projects and deliverables",
        "project experience",
        "academic projects",
        "personal projects",
        "selected projects",
        "key projects",
        "portfolio",
        "project portfolio"
    ],

    "certifications": [
        "certifications",
        "certification",
        "certifications licenses",
        "certifications and licenses",
        "licenses certifications",
        "certificates",
        "courses certifications",
        "courses and certifications",
        "professional certifications",
        "certifications training",
        "certification training",
        "certificates and training",
        "certifications and training",
        "courses training",
        "courses and training"
    ],

    "other": [
        "professional summary",
        "summary",
        "profile",
        "objective",
        "core skills",
        "skills",
        "technical skills",
        "tools technologies",
        "tools and technologies",
        "tools",
        "languages",
        "awards honors",
        "awards and honors",
        "achievements",
        "publications",
        "interests",
        "references"
    ]
}


# --------------------------------------------------
# 4. NORMALIZE AND IDENTIFY HEADINGS
# --------------------------------------------------

def normalize_heading(line):
    line = line.strip().lower()

    line = re.sub(r"^[\W_]+", "", line)
    line = re.sub(r"[\W_]+$", "", line)
    line = re.sub(r"[^a-z0-9 ]", " ", line)

    return " ".join(line.split())


HEADING_LOOKUP = {
    normalize_heading(alias): section
    for section, aliases in SECTION_ALIASES.items()
    for alias in aliases
}


def identify_section(line):
    normalized = normalize_heading(line)

    if normalized in HEADING_LOOKUP:
        return HEADING_LOOKUP[normalized]

    return None


# --------------------------------------------------
# 5. EXTRACT RESUME SECTIONS
# --------------------------------------------------

def extract_sections(text):
    sections = {
        "education": [],
        "experience": [],
        "projects": [],
        "certifications": [],
        "other": []
    }

    current_section = "other"

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        detected_section = identify_section(line)

        if detected_section:
            current_section = detected_section
            continue

        sections[current_section].append(line)

    for section in sections:
        sections[section] = "\n".join(
            sections[section]
        ).strip()

    return sections


# --------------------------------------------------
# 6. FALLBACK EDUCATION EXTRACTION
# --------------------------------------------------


def extract_education_fallback(text):
    """
    Extracts the complete education block, including
    wrapped institute names, years and percentages.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    education_start = re.compile(
        r"^(education|examination|degree/certificate)$",
        re.IGNORECASE
    )

    education_end = re.compile(
        r"^(certifications?\s*(?:&|and)\s*(?:training|licenses?)|"
        r"professional summary|core skills|technical skills|"
        r"relevant courses|projects(?:\s*/\s*deliverables)?|"
        r"experience|work experience|awards\s*/\s*honors|"
        r"languages|tools\s*/\s*technologies)$",
        re.IGNORECASE
    )

    start_index = None

    # Find where education information begins.
    for index, line in enumerate(lines):
        if education_start.match(line):
            start_index = index
            break

    if start_index is None:
        return ""

    education_lines = []

    # Collect every line until the next section.
    for line in lines[start_index:]:

        if education_end.match(line):
            break

        education_lines.append(line)

    return "\n".join(education_lines).strip()

# --------------------------------------------------
# 7. FALLBACK CERTIFICATION EXTRACTION
# --------------------------------------------------

def extract_certifications_fallback(text):
    """
    Finds certification information when it is present
    outside a clearly identified certifications section.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    certification_pattern = re.compile(
        r"\b(certification|certificate|certified|"
        r"training|course completion)\b",
        re.IGNORECASE
    )

    certification_lines = []

    for index, line in enumerate(lines):
        if certification_pattern.search(line):

            # Include the matching line and the next line
            # where useful, without copying the entire resume.
            certification_lines.append(line)

            if index + 1 < len(lines):
                next_line = lines[index + 1]

                if next_line not in certification_lines:
                    certification_lines.append(next_line)

    return "\n".join(
        dict.fromkeys(certification_lines)
    ).strip()
    
def clean_education_text(education_text):
    """
    Remove contact details and unrelated lines from education.
    """

    cleaned_lines = []

    contact_patterns = [
        r"\bemail\s*:",
        r"\bphone\s*:",
        r"\bmobile\s*:",
        r"\blinkedin\s*:",
        r"\bgithub\s*:",
        r"\bleetcode\s*:"
    ]

    for line in education_text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Skip lines containing contact information.
        if any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in contact_patterns
        ):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def remove_education_block_from_other(other_text):
    """
    Remove the education table from the other section,
    while preserving skills, courses and unrelated content.
    """

    lines = other_text.splitlines()

    cleaned_lines = []
    inside_education = False

    education_start = re.compile(
        r"^\s*(examination|degree/certificate)\s*$",
        re.IGNORECASE
    )

    education_end = re.compile(
        r"^\s*(relevant courses|certifications|"
        r"technical skills|skills|languages|"
        r"technologies)\b",
        re.IGNORECASE
    )

    for line in lines:

        if education_start.search(line):
            inside_education = True
            continue

        if inside_education:

            if education_end.search(line):
                inside_education = False
                cleaned_lines.append(line)

            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()



# --------------------------------------------------
# 8. EXTRACT SKILLS AND EVIDENCE
# --------------------------------------------------

def extract_skills(text):
    found_skills = []
    skill_evidence = {}

    lines = text.splitlines()

    for skill, variations in SKILL_KEYWORDS.items():

        matching_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            for variation in variations:
                pattern = re.compile(
                    r"(?<!\w)" + re.escape(variation) + r"(?!\w)",
                    re.IGNORECASE
                )

                if pattern.search(line):
                    matching_lines.append(line)
                    break

        if matching_lines:
            found_skills.append(skill)

            skill_evidence[skill] = list(
                dict.fromkeys(matching_lines)
            )[:3]

    return found_skills, skill_evidence


# --------------------------------------------------
# 9. CREATE CANDIDATE PROFILE
# --------------------------------------------------

def extract_candidate(resume):
    filename = resume.get("filename", "unknown")
    text = resume.get("cleaned_text", "").strip()

    if not text:
        return {
            "filename": filename,
            "status": "insufficient_data",
            "skills": [],
            "skill_evidence": {},
            "education": "",
            "experience": "",
            "projects": "",
            "certifications": "",
            "other": "",
            "missing_fields": [
                "skills",
                "education",
                "experience",
                "projects",
                "certifications"
            ],
            "review_required": True,
            "review_reason": "No extractable resume text"
        }

    sections = extract_sections(text)

    # Extract skills from the complete resume.
    skills, skill_evidence = extract_skills(text)

    # Education fallback.
    
# Education fallback.
    if not sections["education"]:
        sections["education"] = extract_education_fallback(text)

# Clean education even if it was extracted normally.
    sections["education"] = clean_education_text(
        sections["education"]
    )

# Remove duplicated education table from other.
    sections["other"] = remove_education_block_from_other(
        sections["other"]
    )


    # Certification fallback.
    if not sections["certifications"]:
        sections["certifications"] = (
            extract_certifications_fallback(text)
        )

    # Identify missing fields after all extraction attempts.
    missing_fields = []

    for field in [
        "education",
        "experience",
        "projects",
        "certifications"
    ]:
        if not sections[field]:
            missing_fields.append(field)

    if not skills:
        missing_fields.append("skills")

    # Flag genuinely insufficient profiles.
    available_sections = sum(
        bool(sections[field])
        for field in ["education", "experience", "projects"]
    )

    review_required = (
        len(text) < 100
        or available_sections == 0
    )

    if len(text) < 100:
        review_reason = "Very little extractable resume information"
    elif available_sections == 0:
        review_reason = (
            "Major candidate information could not be identified"
        )
    else:
        review_reason = None

    return {
        "filename": filename,
        "status": "processed",
        "skills": skills,
        "skill_evidence": skill_evidence,
        "education": sections["education"],
        "experience": sections["experience"],
        "projects": sections["projects"],
        "certifications": sections["certifications"],
        "other": sections["other"],
        "missing_fields": missing_fields,
        "review_required": review_required,
        "review_reason": review_reason
    }


# --------------------------------------------------
# 10. PROCESS ALL CANDIDATES
# --------------------------------------------------

def main():

    if not INPUT_FILE.exists():
        print("Error: cleaned_resumes.json was not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        resumes = json.load(file)

    candidate_profiles = []

    for resume in resumes:
        profile = extract_candidate(resume)
        candidate_profiles.append(profile)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            candidate_profiles,
            file,
            indent=4,
            ensure_ascii=False
        )

    total = len(candidate_profiles)

    processed = sum(
        1 for profile in candidate_profiles
        if profile["status"] == "processed"
    )

    review_count = sum(
        1 for profile in candidate_profiles
        if profile["review_required"]
    )

    print("\nCandidate extraction completed!")
    print("--------------------------------")
    print(f"Total resumes: {total}")
    print(f"Successfully processed: {processed}")
    print(f"Needs manual review: {review_count}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
