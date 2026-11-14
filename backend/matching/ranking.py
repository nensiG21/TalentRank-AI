
import json
from pathlib import Path

try:
    from .duplicate_detector import detect_duplicates
except ImportError:
    from duplicate_detector import detect_duplicates


BASE_DIR = Path(__file__).resolve().parents[1]

PROCESSED_DIR = BASE_DIR / "data" / "processed"

INPUT_FILE = PROCESSED_DIR / "candidate_classifications.json"
PROFILES_FILE = PROCESSED_DIR / "candidate_profiles.json"
OUTPUT_FILE = PROCESSED_DIR / "ranked_candidates.json"


def rank_candidates(candidates, role):
    """Rank candidates while excluding flagged duplicate records."""

    ranked = []

    for candidate in candidates:

        # Keep duplicate records in the dataset, but don't rank them.
        if candidate.get("duplicate_status") == "duplicate":
            continue

        role_result = candidate.get(role, {})

        ranked.append({
            "filename": candidate.get("filename"),
            "category": candidate.get("category"),
            "score": role_result.get("score", 0),
            "matched_requirements": role_result.get(
                "matched_requirements", []
            ),
            "missing_requirements": role_result.get(
                "missing_requirements", []
            ),
            "manual_review_required": candidate.get(
                "manual_review_required", False
            ),
            "classification_reason": candidate.get(
                "classification_reason", ""
            ),
            "duplicate_group_id": candidate.get("duplicate_group_id"),
            "duplicate_status": candidate.get(
                "duplicate_status", "unique"
            ),
            "duplicate_review_required": candidate.get(
                "duplicate_review_required", False
            ),
        })

    ranked.sort(
        key=lambda candidate: candidate["score"],
        reverse=True
    )

    for position, candidate in enumerate(ranked, start=1):
        candidate["rank"] = position

    return ranked


def main():

    if not INPUT_FILE.exists():
        print("Classification file not found!")
        print(f"Expected location: {INPUT_FILE}")
        return

    if not PROFILES_FILE.exists():
        print("Candidate profiles file not found!")
        print(f"Expected location: {PROFILES_FILE}")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        candidates = json.load(file)

    with open(PROFILES_FILE, "r", encoding="utf-8") as file:
        profiles = json.load(file)

    if len(candidates) != len(profiles):
        print("Error: Candidate classifications and profiles have")
        print("different record counts. Please check the pipeline.")
        return

    # Detect duplicate groups using the complete candidate profiles.
    duplicate_info = detect_duplicates(profiles)

    # Store duplicate information in both datasets.
    for profile, candidate, duplicate in zip(
        profiles, candidates, duplicate_info
    ):
        profile.update(duplicate)
        candidate.update(duplicate)

    # Save updated records without deleting any candidates.
    with open(PROFILES_FILE, "w", encoding="utf-8") as file:
        json.dump(profiles, file, indent=4, ensure_ascii=False)

    with open(INPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(candidates, file, indent=4, ensure_ascii=False)

    lca_ranking = rank_candidates(candidates, "lca")
    uiux_ranking = rank_candidates(candidates, "ui_ux")

    duplicate_count = sum(
        1 for item in duplicate_info
        if item["duplicate_status"] == "duplicate"
    )

    duplicate_groups = len({
        item["duplicate_group_id"]
        for item in duplicate_info
        if item["duplicate_group_id"]
    })

    output = {
        "total_candidates": len(candidates),
        "unique_candidates": len(candidates) - duplicate_count,
        "duplicate_records_excluded": duplicate_count,
        "duplicate_groups": duplicate_groups,
        "ranking_method": (
            "Candidates are ranked by preliminary role match score. "
            "Likely duplicate records are retained for HR review but "
            "excluded from role rankings. Scores are evidence-based "
            "prototype estimates, not validated hiring assessments."
        ),
        "lca_ranking": lca_ranking,
        "ui_ux_ranking": uiux_ranking
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=4, ensure_ascii=False)

    print("\nCandidate ranking completed!")
    print("--------------------------------")
    print(f"Total records: {len(candidates)}")
    print(f"Duplicate groups: {duplicate_groups}")
    print(f"Duplicate records excluded: {duplicate_count}")
    print(f"Unique candidates retained: {len(candidates) - duplicate_count}")

    print("\nTop 5 LCA candidates:")
    for candidate in lca_ranking[:5]:
        print(
            f'{candidate["rank"]}. '
            f'{candidate["filename"]} '
            f'| Score: {candidate["score"]}%'
        )

    print("\nTop 5 UI/UX candidates:")
    for candidate in uiux_ranking[:5]:
        print(
            f'{candidate["rank"]}. '
            f'{candidate["filename"]} '
            f'| Score: {candidate["score"]}%'
        )

    print(f"\nOutput saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
