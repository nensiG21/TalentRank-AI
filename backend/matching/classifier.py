
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = BASE_DIR / "data" / "processed" / "candidate_profiles.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "candidate_classifications.json"


# ==================================================
# 1. ROLE REQUIREMENTS
# ==================================================

ROLES = {
    "lca": {
        "Life Cycle Assessment": {
            "weight": 5,
            "keywords": ["life cycle assessment", "lca"]
        },
        "Life Cycle Inventory": {
            "weight": 5,
            "keywords": ["life cycle inventory", "lci"]
        },
        "SimaPro": {
            "weight": 4,
            "keywords": ["simapro"]
        },
        "GaBi": {
            "weight": 4,
            "keywords": ["gabi", "sphera gabi"]
        },
        "OpenLCA": {
            "weight": 4,
            "keywords": ["openlca", "open lca"]
        },
        "ISO 14040/14044": {
            "weight": 4,
            "keywords": ["iso 14040", "iso 14044", "14040/14044"]
        },
        "EPD": {
            "weight": 3,
            "keywords": ["environmental product declaration", "epd"]
        },
        "Carbon Accounting": {
            "weight": 2,
            "keywords": ["carbon accounting"]
        },
        "Sustainability": {
            "weight": 2,
            "keywords": ["sustainability"]
        },
        "Environmental Impact Assessment": {
            "weight": 2,
            "keywords": ["environmental impact assessment", "eia"]
        },
        "Data Analysis": {
            "weight": 1,
            "keywords": ["data analysis", "data analytics"]
        },
        "Excel": {
            "weight": 1,
            "keywords": ["excel", "microsoft excel"]
        }
    },

    "ui_ux": {
        "UI/UX Design": {
            "weight": 5,
            "keywords": [
                "ui/ux", "ui ux", "ux/ui",
                "ux design", "ui design",
                "user interface design",
                "user flows",
                "information architecture",
                "interaction design",
                "user-centered design",
                "user centred design",
                "interface design"
            ]
        },
        "Figma": {
            "weight": 5,
            "keywords": ["figma"]
        },
        "Wireframing": {
            "weight": 4,
            "keywords": [
                "wireframing", "wireframe",
                "low fidelity", "low-fidelity"
            ]
        },
        "Prototyping": {
            "weight": 4,
            "keywords": [
                "prototyping", "prototype",
                "high fidelity prototype",
                "high-fidelity prototype"
            ]
        },
        "User Research": {
            "weight": 4,
            "keywords": [
                "user research",
                "user interviews",
                "user needs",
                "user behavior",
                "user behaviour"
            ]
        },
        "Usability Testing": {
            "weight": 4,
            "keywords": [
                "usability testing",
                "accessibility testing",
                "user testing"
            ]
        },
        "Adobe XD": {
            "weight": 2,
            "keywords": ["adobe xd"]
        },
        "Photoshop": {
            "weight": 1,
            "keywords": ["photoshop"]
        },
        "Illustrator": {
            "weight": 1,
            "keywords": ["illustrator", "adobe illustrator"]
        },
        "Responsive Design": {
            "weight": 2,
            "keywords": [
                "responsive design",
                "mobile interface",
                "mobile app design"
            ]
        },
        "HTML": {
            "weight": 1,
            "keywords": ["html"]
        },
        "CSS": {
            "weight": 1,
            "keywords": ["css"]
        }
    }
}


# ==================================================
# 2. EVIDENCE WEIGHTS
# ==================================================

SOURCE_WEIGHTS = {
    "experience": 1.0,
    "projects": 1.0,
    "methods": 0.6,
    "domain": 0.6,
    "summary": 0.4,
    "skills": 0.4,
    "platforms": 0.2,
    "other": 0.4
}


# ==================================================
# 3. EXTRACT CANDIDATE SECTIONS
# ==================================================

def extract_lines(value):

    lines = []

    if isinstance(value, str):
        lines.extend(
            line.strip()
            for line in value.splitlines()
            if line.strip()
        )

    elif isinstance(value, list):
        for item in value:
            lines.extend(extract_lines(item))

    elif isinstance(value, dict):
        for item in value.values():
            lines.extend(extract_lines(item))

    return lines


def get_candidate_sections(profile):

    sections = {
        "experience": [],
        "projects": [],
        "skills": [],
        "other": [],
        "summary": []
    }

    for key in ["experience", "projects", "skills", "other", "summary"]:

        if key in profile:
            sections[key].extend(extract_lines(profile[key]))

    profile_sections = profile.get("sections", {})

    if isinstance(profile_sections, dict):

        for key, value in profile_sections.items():

            key_lower = key.lower().strip()

            if key_lower in sections:
                sections[key_lower].extend(extract_lines(value))
            else:
                sections["other"].extend(extract_lines(value))

    evidence = profile.get("evidence", {})

    if isinstance(evidence, dict):

        for key, value in evidence.items():

            key_lower = key.lower().strip()

            if key_lower in sections:
                sections[key_lower].extend(extract_lines(value))

    elif isinstance(evidence, list):
        sections["other"].extend(extract_lines(evidence))

    for key in sections:
        sections[key] = list(dict.fromkeys(sections[key]))

    return sections


# ==================================================
# 4. EVIDENCE SOURCE WEIGHT
# ==================================================

def get_source_weight(source, line):

    if source == "experience":
        return SOURCE_WEIGHTS["experience"]

    if source == "projects":
        return SOURCE_WEIGHTS["projects"]

    if source == "skills":
        return SOURCE_WEIGHTS["skills"]

    if source == "summary":
        return SOURCE_WEIGHTS["summary"]

    if source == "other":

        lower_line = line.lower().strip()

        if lower_line.startswith("platforms:"):
            return SOURCE_WEIGHTS["platforms"]

        if lower_line.startswith("methods:"):
            return SOURCE_WEIGHTS["methods"]

        if lower_line.startswith("domain knowledge:"):
            return SOURCE_WEIGHTS["domain"]

        return SOURCE_WEIGHTS["other"]

    return 0.4


# ==================================================
# 5. KEYWORD MATCHING
# ==================================================

def keyword_found(text, keywords):

    text = text.lower()

    for keyword in keywords:

        pattern = (
            r"(?<!\w)"
            + re.escape(keyword.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text):
            return True

    return False


# ==================================================
# 6. ROLE SCORE CALCULATION
# ==================================================

def calculate_role_score(sections, role):

    requirements = ROLES[role]

    earned_points = 0

    total_possible_points = sum(
        item["weight"]
        for item in requirements.values()
    )

    matched_requirements = []
    missing_requirements = []

    for requirement, details in requirements.items():

        requirement_weight = details["weight"]
        keywords = details["keywords"]

        evidence_found = []

        for source, lines in sections.items():

            for line in lines:

                if keyword_found(line, keywords):

                    credit = get_source_weight(source, line)

                    evidence_found.append({
                        "source": source,
                        "text": line,
                        "credit": credit
                    })

        if evidence_found:

            best_credit = max(
                item["credit"]
                for item in evidence_found
            )

            points = requirement_weight * best_credit

            earned_points += points

            matched_requirements.append({
                "requirement": requirement,
                "possible_points": requirement_weight,
                "earned_points": round(points, 2),
                "evidence": evidence_found
            })

        else:
            missing_requirements.append(requirement)

    score = (
        earned_points / total_possible_points * 100
        if total_possible_points else 0
    )

    return {
        "score": round(score, 2),
        "earned_points": round(earned_points, 2),
        "total_possible_points": total_possible_points,
        "matched_requirements": matched_requirements,
        "missing_requirements": missing_requirements
    }


# ==================================================
# 7. DIRECT ROLE EVIDENCE
# ==================================================

def has_direct_role_evidence(sections, role):

    direct_lines = (
        sections.get("experience", [])
        + sections.get("projects", [])
    )

    requirements = ROLES[role]

    if role == "lca":

        core_requirements = [
            "Life Cycle Assessment",
            "Life Cycle Inventory",
            "SimaPro",
            "GaBi",
            "OpenLCA",
            "ISO 14040/14044"
        ]

    else:

        core_requirements = [
            "UI/UX Design",
            "Figma",
            "Wireframing",
            "Prototyping",
            "User Research",
            "Usability Testing"
        ]

    for requirement in core_requirements:

        keywords = requirements[requirement]["keywords"]

        for line in direct_lines:

            if keyword_found(line, keywords):
                return True

    return False


# ==================================================
# 8. LCA PROJECT REVIEW
# ==================================================

def get_lca_project_evidence(sections):

    evidence = []

    project_keywords = [
        "life cycle assessment",
        "lca",
        "life cycle inventory",
        "lci",
        "openlca",
        "simapro",
        "gabi",
        "environmental product declaration"
    ]

    for line in sections.get("projects", []):

        if keyword_found(line, project_keywords):
            evidence.append(line)

    return {
        "lca_related_project_lines_found": len(evidence),
        "evidence": evidence,
        "verified_completed_project_count": None,
        "note": (
            "Extracted lines are evidence for HR review. "
            "They do not represent a verified count of distinct "
            "completed LCA projects."
        )
    }


# ==================================================
# 9. EXPERIENCE REVIEW
# ==================================================

def get_experience_review(sections):

    evidence = []

    duration_pattern = re.compile(
        r"\b\d+\s*\+?\s*(?:years?|yrs?)\b",
        re.IGNORECASE
    )

    all_lines = (
        sections.get("experience", [])
        + sections.get("summary", [])
        + sections.get("other", [])
    )

    for line in all_lines:

        matches = duration_pattern.findall(line)

        for match in matches:
            evidence.append(match)

    return {
        "duration_mentions_found": list(dict.fromkeys(evidence)),
        "verified_years": None,
        "note": (
            "Duration mentions need date-based HR verification. "
            "They are not treated as verified total experience."
        )
    }


# ==================================================
# 10. CLASSIFICATION
# ==================================================

def classify_candidate(lca_result, uiux_result, sections):

    lca_score = lca_result["score"]
    uiux_score = uiux_result["score"]

    lca_direct = has_direct_role_evidence(sections, "lca")
    uiux_direct = has_direct_role_evidence(sections, "ui_ux")

    lca_qualified = lca_score >= 30 and lca_direct

    # UI/UX projects count as direct evidence.
    # Professional experience is not mandatory for this internship.
    uiux_qualified = uiux_score >= 35 and uiux_direct

    if lca_qualified and uiux_qualified:

        category = "Both"
        reason = "Strong direct evidence found for both roles."

    elif lca_qualified:

        category = "LCA"
        reason = (
            "Relevant LCA experience or project evidence found. "
            "Years of experience and completed projects require HR verification."
        )

    elif uiux_qualified:

        category = "UI/UX"
        reason = (
            "Relevant UI/UX project or experience evidence found. "
            "Portfolio and design quality require HR review."
        )

    else:

        category = "Neither / Uncertain"
        reason = (
            "Current evidence does not meet the role classification "
            "criteria. Human review is recommended."
        )

    return category, reason, lca_qualified, uiux_qualified


# ==================================================
# 11. MAIN PROCESS
# ==================================================

def process_candidates():

    if not INPUT_FILE.exists():

        print("Candidate profiles file not found:", INPUT_FILE)
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        candidates = json.load(file)

    results = []

    for profile in candidates:

        sections = get_candidate_sections(profile)

        lca_result = calculate_role_score(sections, "lca")
        uiux_result = calculate_role_score(sections, "ui_ux")

        (
            category,
            reason,
            lca_qualified,
            uiux_qualified
        ) = classify_candidate(
            lca_result,
            uiux_result,
            sections
        )

        lca_project_review = get_lca_project_evidence(sections)

        experience_review = get_experience_review(sections)

        manual_review_required = (
            lca_qualified
            or category == "Neither / Uncertain"
            or bool(profile.get("review_flags"))
            or bool(profile.get("missing_fields"))
        )

        results.append({

            "filename": profile.get("filename", "Unknown"),

            "category": category,

            "classification_reason": reason,

            "lca": lca_result,

            "ui_ux": uiux_result,

            "lca_project_review": lca_project_review,

            "experience_review": experience_review,

            "manual_review_required": manual_review_required,

            "role_evidence": {
                "lca_direct_evidence": lca_qualified,
                "ui_ux_direct_evidence": uiux_qualified
            }
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\nCandidate classification completed!")
    print("--------------------------------")

    print("Total candidates:", len(results))

    for category in [
        "LCA",
        "UI/UX",
        "Both",
        "Neither / Uncertain"
    ]:

        count = sum(
            1 for candidate in results
            if candidate["category"] == category
        )

        print(f"{category}: {count}")

    manual_count = sum(
        1 for candidate in results
        if candidate["manual_review_required"]
    )

    print("\nCandidates requiring manual review:", manual_count)

    print("\nOutput saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    process_candidates()
