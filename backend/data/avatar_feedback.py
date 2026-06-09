from datetime import datetime


AVATAR_FEEDBACK_LOG: list[dict] = []


def record_avatar_feedback(*, patient_id: str, rating: int, comment: str | None = None) -> dict:
    entry = {
        "patient_id": patient_id,
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow(),
    }
    AVATAR_FEEDBACK_LOG.append(entry)
    return entry


def build_avatar_feedback_summary(patient_id: str | None = None) -> dict:
    entries = [
        entry for entry in AVATAR_FEEDBACK_LOG
        if patient_id is None or entry["patient_id"] == patient_id
    ]
    breakdown = {str(score): 0 for score in range(1, 6)}
    for entry in entries:
        breakdown[str(entry["rating"])] += 1

    total = len(entries)
    average = round(sum(entry["rating"] for entry in entries) / total, 2) if total else None
    return {
        "patient_id": patient_id,
        "total_ratings": total,
        "average_rating": average,
        "ratings_breakdown": breakdown,
    }