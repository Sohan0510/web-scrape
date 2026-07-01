"""
Batch Runner
=============
Orchestrates batch scraping of multiple USNs with automatic retry,
progress callbacks, and Excel export.
"""

import sys
import io
import os
import time
import glob
from datetime import datetime
from src.scraper import fetch_student_result
from src.database import save_or_update_result, get_results_by_usn_range
from src.exporter import export_to_excel
from src.config import EXPORTS_DIR, TEMP_DIR

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def generate_usns(college_code, year, branch, start_roll, end_roll):
    """
    Generates a list of USNs from the pattern.
    Example: generate_usns("1RF", "23", "CS", 1, 5) -> ["1RF23CS001", ..., "1RF23CS005"]
    """
    usns = []
    for roll in range(start_roll, end_roll + 1):
        usn = f"{college_code}{year}{branch}{roll:03d}"
        usns.append(usn.upper())
    return usns


def _cleanup_old_exports(prefix, keep_latest=2):
    """Remove old export files, keeping only the latest N."""
    pattern = os.path.join(EXPORTS_DIR, f"{prefix}*.xlsx")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    for old_file in files[keep_latest:]:
        try:
            os.remove(old_file)
        except OSError:
            pass


def _cleanup_temp():
    """Remove all files from the temp directory."""
    if os.path.exists(TEMP_DIR):
        for f in os.listdir(TEMP_DIR):
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except OSError:
                pass


def _process_single_usn(usn, url, is_reval, max_retries):
    """
    Processes a single USN: scrape -> save to DB.
    Returns (status_string, detail_dict_or_none).
    """
    result = fetch_student_result(usn, url, max_retries=max_retries)
    
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            print(f"   [!] {usn}: Not found / no results")
            return "not_found", None
        else:
            print(f"   [X] {usn}: {error_msg}")
            return "failed", None
    
    # Save to MongoDB
    db_status, db_msg = save_or_update_result(
        {
            "usn": result["usn"],
            "name": result["name"],
            "subjects": result["subjects"],
            "grand_total": result["grand_total"],
            "url_source": url,
            "reval_status": result.get("reval_status")
        },
        is_reval=is_reval
    )
    print(f"   {db_msg}")
    
    if db_status == "not_applied":
        detail = {
            "usn": usn,
            "name": result["name"],
            "grand_total": result["grand_total"],
            "subjects_count": len(result["subjects"]),
            "attempts": result.get("attempts", 0),
            "db_status": db_status
        }
        return "success", detail
    
    if db_status == "unchanged":
        return "unchanged", None
    
    detail = {
        "usn": usn,
        "name": result["name"],
        "grand_total": result["grand_total"],
        "subjects_count": len(result["subjects"]),
        "attempts": result.get("attempts", 0),
        "db_status": db_status
    }
    print(f"   [OK] {usn}: {result['name']} -- Total: {result['grand_total']} (Attempt {result.get('attempts', '?')})")
    
    if db_status == "updated":
        return "updated", detail
    return "success", detail


def run_batch(url, usns, is_reval=False, delay=0.5, max_retries=15,
              retry_rounds=2, progress_callback=None):
    """
    Processes a batch of USNs with automatic retry rounds for failures.
    """
    total = len(usns)
    results = {
        "success": [],
        "failed": [],
        "not_found": [],
        "unchanged": [],
    }
    
    start_time = time.time()
    processed_count = 0
    
    print(f"\n{'='*60}")
    print(f"  VTU RESULT SCRAPER -- {'REVALUATION' if is_reval else 'BATCH'} MODE")
    print(f"  URL: {url}")
    print(f"  Students: {total}  |  Retry rounds: {retry_rounds}")
    print(f"  Started: {datetime.now().strftime('%I:%M:%S %p')}")
    print(f"{'='*60}\n")
    
    pending_usns = list(usns)
    
    for round_num in range(1, 2 + retry_rounds):
        if not pending_usns:
            break
        
        round_label = "INITIAL PASS" if round_num == 1 else f"RETRY ROUND {round_num - 1}/{retry_rounds}"
        print(f"\n  --- {round_label} ({len(pending_usns)} students) ---\n")
        
        failed_this_round = []
        
        for i, usn in enumerate(pending_usns, 1):
            processed_count += 1
            print(f"\n[{processed_count}/{total}] Processing {usn}... ({round_label})")
            
            status, detail = _process_single_usn(usn, url, is_reval, max_retries)
            
            if status == "success" or status == "updated":
                results["success"].append(detail)
            elif status == "not_found":
                results["not_found"].append(usn)
            elif status == "unchanged":
                results["unchanged"].append(usn)
            elif status == "failed":
                failed_this_round.append(usn)
            
            if progress_callback:
                progress_callback(
                    min(processed_count, total),
                    total, usn, status
                )
            
            if i < len(pending_usns):
                time.sleep(delay)
        
        if not failed_this_round:
            print(f"\n  --- No failures! Skipping remaining retries. ---")
            break
        
        if round_num <= retry_rounds:
            print(f"\n  --- {len(failed_this_round)} failed. Will retry... ---")
            pending_usns = failed_this_round
            time.sleep(2)
        else:
            results["failed"].extend(failed_this_round)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Success:    {len(results['success'])}")
    print(f"  Failed:     {len(results['failed'])}")
    print(f"  Not Found:  {len(results['not_found'])}")
    if is_reval:
        print(f"  Unchanged:  {len(results['unchanged'])}")
    print(f"  Time:       {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"{'='*60}")
    
    if results["failed"]:
        print(f"\n  Still failed after retries: {', '.join(results['failed'])}")
    
    # Cleanup temp files after batch
    _cleanup_temp()
    
    return {
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "not_found_count": len(results["not_found"]),
        "unchanged_count": len(results["unchanged"]),
        "elapsed_seconds": elapsed,
        "details": results
    }


def run_batch_and_export(url, usns, is_reval=False, delay=0.5, max_retries=15,
                          retry_rounds=2, export_prefix="results",
                          progress_callback=None):
    """
    Runs the batch scraper AND exports results to Excel.
    Excel filename uses the USN range (e.g., 1RF23CS001_to_1RF23CS005).
    Only exports the USNs from this batch, not the entire DB.
    """
    summary = run_batch(
        url=url,
        usns=usns,
        is_reval=is_reval,
        delay=delay,
        max_retries=max_retries,
        retry_rounds=retry_rounds,
        progress_callback=progress_callback
    )
    
    # Export only the USNs from this batch
    batch_results = get_results_by_usn_range(usns)
    
    excel_path = None
    if batch_results:
        # Build filename from USN range: e.g. 1RF23CS001_to_1RF23CS005
        first_usn = usns[0]
        last_usn = usns[-1]
        range_prefix = f"{first_usn}_to_{last_usn}"
        
        # Cleanup old exports for this range
        _cleanup_old_exports(range_prefix, keep_latest=1)
        
        excel_path = export_to_excel(batch_results, prefix=range_prefix)
    else:
        print("\n[!] No results in database to export.")
    
    return summary, excel_path
