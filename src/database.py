"""
MongoDB Database Layer
=======================
Handles all student result storage and retrieval.

Key design: Subjects from different semesters ACCUMULATE in one document.
Each subject is keyed by its code (e.g. BCS501). Scraping a new semester
URL won't delete subjects from other semesters already stored.
"""

# pyrefly: ignore [missing-import]
from pymongo import MongoClient, ASCENDING
from src.config import MONGO_URI, DB_NAME
from datetime import datetime

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db["results"]

# Create indexes for fast lookups
collection.create_index("usn", unique=True)
collection.create_index([("name", ASCENDING)])


def save_or_update_result(student_data, is_reval=False):
    """
    Saves a new student record or MERGES into an existing one.
    
    Name handling:
    - Always updates the name if the new scrape has a non-empty name
    - Keeps the existing name if the new scrape returns empty
    
    For revaluation runs:
    - Compares EACH subject's total marks individually
    - Only updates subjects where new marks > old marks
    
    Returns (status_string, message_string).
    """
    usn = student_data.get("usn")
    if not usn:
        return "error", "Invalid data: No USN found."

    existing_record = collection.find_one({"usn": usn})
    now = datetime.utcnow().isoformat()
    new_subjects = student_data.get("subjects", {})
    new_url = student_data.get("url_source", "")
    new_name = student_data.get("name", "").strip()

    # Mark all incoming subjects as not reval-updated
    for sub_code in new_subjects:
        new_subjects[sub_code]["reval_updated"] = False

    # ── NEW ENTRY ──
    if not existing_record:
        semesters_found = sorted(set(
            s.get("semester", 0) for s in new_subjects.values()
        ))
        
        student_data["scraped_at"] = now
        student_data["last_updated"] = now
        student_data["reval_changes"] = []
        student_data["url_sources"] = [new_url] if new_url else []
        student_data["semesters"] = semesters_found
        student_data["subjects"] = new_subjects
        student_data["grand_total"] = sum(
            s.get("total", 0) for s in new_subjects.values()
        )
        
        collection.insert_one(student_data)
        sem_label = ", ".join(str(s) for s in semesters_found) if semesters_found else "?"
        if student_data.get("reval_status") == "Not Applied":
            return "not_applied", f"[-] Not applied for reval: {usn}"
        return "inserted", f"[+] New: {usn} ({new_name or '?'}) Sem {sem_label}"

    # ── EXISTING ENTRY ──
    old_subjects = existing_record.get("subjects", {})
    old_url_sources = existing_record.get("url_sources", [])
    
    # Name resolution: prefer non-empty name, prioritize new scrape data
    existing_name = existing_record.get("name", "").strip()
    resolved_name = new_name if new_name else existing_name

    if is_reval:
        if student_data.get("reval_status") == "Not Applied":
            collection.update_one({"usn": usn}, {"$set": {"reval_status": "Not Applied", "last_updated": now}})
            return "not_applied", f"[-] Not applied for reval: {usn}"
            
        return _handle_reval_update(
            usn, resolved_name, new_subjects, old_subjects,
            existing_record, old_url_sources, new_url, now, student_data.get("reval_status")
        )
    else:
        return _handle_normal_merge(
            usn, resolved_name, new_subjects, old_subjects,
            existing_record, old_url_sources, new_url, now
        )


def _handle_reval_update(usn, name, new_subjects, old_subjects,
                          existing_record, old_url_sources, new_url, now, reval_status):
    """Revaluation: compare per-subject, only update if marks improved."""
    merged_subjects = dict(old_subjects)
    updates_made = []
    
    for sub_code, new_data in new_subjects.items():
        old_data = old_subjects.get(sub_code, {})
        old_total = old_data.get("total", 0)
        new_total = new_data.get("total", 0)
        
        if sub_code not in old_subjects:
            # New subject not in DB — add it
            merged_subjects[sub_code] = new_data
            updates_made.append(f"  NEW: {sub_code} = {new_total}")
        elif new_total > old_total:
            # Marks improved — update with reval data
            new_data["reval_updated"] = True
            new_data["old_total"] = old_total
            merged_subjects[sub_code] = new_data
            updates_made.append(f"  UP:  {sub_code} {old_total} -> {new_total}")
    
    if updates_made:
        grand_total = sum(s.get("total", 0) for s in merged_subjects.values())
        semesters = sorted(set(
            s.get("semester", 0) for s in merged_subjects.values()
        ))
        
        reval_log = {
            "date": now,
            "changes": updates_made,
            "old_grand_total": existing_record.get("grand_total", 0),
            "new_grand_total": grand_total
        }
        
        url_sources = list(set(old_url_sources + ([new_url] if new_url else [])))
        
        collection.update_one(
            {"usn": usn},
            {"$set": {
                "subjects": merged_subjects,
                "grand_total": grand_total,
                "semesters": semesters,
                "last_updated": now,
                "url_sources": url_sources,
                "name": name,
                "reval_status": reval_status
            },
            "$push": {"reval_changes": reval_log}}
        )
        return "updated", f"[^] Reval {usn}: {len(updates_made)} subjects updated"
    else:
        # Update name and reval_status even if marks are unchanged
        update_fields = {"last_updated": now}
        if name and name != existing_record.get("name", "").strip():
            update_fields["name"] = name
        if reval_status:
            update_fields["reval_status"] = reval_status
            
        collection.update_one({"usn": usn}, {"$set": update_fields})
        return "unchanged", f"[-] No improvement for {usn}"


def _handle_normal_merge(usn, name, new_subjects, old_subjects,
                          existing_record, old_url_sources, new_url, now):
    """Normal scrape: merge new subjects into existing record."""
    merged_subjects = dict(old_subjects)
    new_count = 0
    updated_count = 0
    
    for sub_code, new_data in new_subjects.items():
        if sub_code not in old_subjects:
            new_count += 1
        else:
            updated_count += 1
        merged_subjects[sub_code] = new_data
    
    grand_total = sum(s.get("total", 0) for s in merged_subjects.values())
    semesters = sorted(set(
        s.get("semester", 0) for s in merged_subjects.values()
    ))
    url_sources = list(set(old_url_sources + ([new_url] if new_url else [])))
    
    collection.update_one(
        {"usn": usn},
        {"$set": {
            "subjects": merged_subjects,
            "grand_total": grand_total,
            "semesters": semesters,
            "last_updated": now,
            "url_sources": url_sources,
            "name": name,
            "reval_changes": existing_record.get("reval_changes", [])
        }}
    )
    
    kept = len(old_subjects) - updated_count
    return "merged", f"[+] Merged {usn}: +{new_count} new, {updated_count} refreshed, {kept} kept"


def get_all_results(url_filter=None):
    """Returns all student records from the database."""
    query = {}
    if url_filter:
        query["url_sources"] = url_filter
    return list(collection.find(query, {"_id": 0}))


def get_result_by_usn(usn):
    """Returns a single student record by USN."""
    return collection.find_one({"usn": usn}, {"_id": 0})


def get_results_count():
    """Returns the total number of records."""
    return collection.count_documents({})


def get_results_by_usn_range(usns):
    """Returns student records for a list of USNs, preserving order."""
    results = list(collection.find({"usn": {"$in": usns}}, {"_id": 0}))
    # Sort by USN to maintain order
    usn_order = {u: i for i, u in enumerate(usns)}
    results.sort(key=lambda r: usn_order.get(r.get("usn", ""), 999))
    return results


def delete_all_results():
    """Clears all records. Use with caution."""
    result = collection.delete_many({})
    return result.deleted_count