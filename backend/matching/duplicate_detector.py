
import re
import hashlib
from difflib import SequenceMatcher


PROFILE_FIELDS = [
    "education",
    "experience",
    "projects",
    "certifications",
    "other",
]


def normalize_text(value):
    """Normalize text for duplicate comparison."""
    if not value:
        return ""

    value = str(value).lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w@.+]", "", value)

    return value.strip()


def extract_email(profile):
    text = profile.get("other", "")
    match = re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        text,
        re.IGNORECASE,
    )
    return match.group(0).lower() if match else ""


def extract_phone(profile):
    text = profile.get("other", "")
    match = re.search(
        r"(?:\+?\d[\d\s()-]{8,}\d)",
        text,
    )

    if not match:
        return ""

    digits = re.sub(r"\D", "", match.group(0))

    return digits if len(digits) >= 10 else ""


def get_profile_text(profile):
    """Combine meaningful resume sections for comparison."""
    parts = []

    for field in PROFILE_FIELDS:
        value = normalize_text(profile.get(field, ""))
        if value:
            parts.append(value)

    return " ".join(parts)


def get_fingerprint(profile):
    """Generate a fingerprint for exact normalized profile matches."""
    content = get_profile_text(profile)

    if not content:
        return ""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compare_profiles(profile_a, profile_b):
    """Return similarity between two resume profiles."""
    text_a = get_profile_text(profile_a)
    text_b = get_profile_text(profile_b)

    if not text_a or not text_b:
        return 0.0

    return SequenceMatcher(
        None,
        text_a,
        text_b
    ).ratio()


def detect_duplicates(profiles):
    """
    Detect likely duplicate resumes.

    All original records are retained.
    One provisional primary record is selected per group.
    """

    count = len(profiles)

    duplicate_info = [
        {
            "duplicate_group_id": None,
            "duplicate_status": "unique",
            "duplicate_of": None,
            "duplicate_reason": None,
            "duplicate_review_required": False,
        }
        for _ in profiles
    ]

    parent = list(range(count))

    def find(index):
        if parent[index] != index:
            parent[index] = find(parent[index])
        return parent[index]

    def union(first, second):
        root_a = find(first)
        root_b = find(second)

        if root_a != root_b:
            parent[root_b] = root_a

    fingerprints = [
        get_fingerprint(profile)
        for profile in profiles
    ]

    emails = [
        extract_email(profile)
        for profile in profiles
    ]

    phones = [
        extract_phone(profile)
        for profile in profiles
    ]

    # Compare every pair of profiles.
    for i in range(count):
        for j in range(i + 1, count):

            same_email = (
                bool(emails[i])
                and emails[i] == emails[j]
            )

            same_phone = (
                bool(phones[i])
                and phones[i] == phones[j]
            )

            exact_content = (
                bool(fingerprints[i])
                and fingerprints[i] == fingerprints[j]
            )

            similarity = compare_profiles(
                profiles[i],
                profiles[j]
            )

            # Strong identity or content match.
            if same_email or exact_content:
                union(i, j)

            # Phone match needs additional profile similarity.
            elif same_phone and similarity >= 0.75:
                union(i, j)

            # Near-duplicate match needs an identity clue.
            elif (
                similarity >= 0.92
                and (same_email or same_phone)
            ):
                union(i, j)

    groups = {}

    for index in range(count):
        root = find(index)
        groups.setdefault(root, []).append(index)

    group_number = 1

    for indexes in groups.values():

        if len(indexes) == 1:
            continue

        group_id = f"DUP-{group_number:03d}"
        group_number += 1

        # Choose the most complete profile as provisional primary.
        primary_index = max(
            indexes,
            key=lambda index: sum(
                len(str(profiles[index].get(field, "")).strip())
                for field in PROFILE_FIELDS
            ),
        )

        for index in indexes:
            if index == primary_index:
                duplicate_info[index] = {
                    "duplicate_group_id": group_id,
                    "duplicate_status": "primary",
                    "duplicate_of": None,
                    "duplicate_reason": (
                        "Provisional primary record in a detected "
                        "duplicate group. HR verification required."
                    ),
                    "duplicate_review_required": True,
                }
            else:
                duplicate_info[index] = {
                    "duplicate_group_id": group_id,
                    "duplicate_status": "duplicate",
                    "duplicate_of": profiles[primary_index].get(
                        "filename"
                    ),
                    "duplicate_reason": (
                        "Likely duplicate resume. Retained for HR review."
                    ),
                    "duplicate_review_required": True,
                }

    return duplicate_info
