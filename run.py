"""
VTU Result Scraper -- Interactive CLI
=====================================
Run this script to start scraping VTU results interactively.

Usage:
    python run.py
"""
import sys
import io
import urllib3
urllib3.disable_warnings()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.batch_runner import generate_usns, run_batch_and_export


def print_banner():
    print("""
+----------------------------------------------------------+
|           VTU RESULT SCRAPER -- BATCH ENGINE              |
|                                                          |
|  Automatically scrape 200+ student results from VTU.     |
|  Solves CAPTCHAs, stores to MongoDB, exports to Excel.    |
+----------------------------------------------------------+
    """)


def get_url():
    print("-" * 50)
    print("STEP 1: Enter the VTU Result URL")
    print("-" * 50)
    print("Example: https://results.vtu.ac.in/D25J26Ecbcs/index.php")
    print()
    url = input("  Paste URL: ").strip()
    
    if not url.startswith("http"):
        print("[!] Invalid URL. Must start with http:// or https://")
        return get_url()
    
    return url


def get_usn_pattern():
    print()
    print("-" * 50)
    print("STEP 2: Enter the USN Pattern")
    print("-" * 50)
    print("A VTU USN looks like: 1RF23CS001")
    print("  1RF  -> College code")
    print("  23   -> Admission year")
    print("  CS   -> Branch code")
    print("  001  -> Roll number")
    print()
    
    college_code = input("  College code (e.g., 1RF): ").strip().upper()
    year = input("  Admission year (e.g., 23): ").strip()
    branch = input("  Branch code (e.g., CS): ").strip().upper()
    
    sample_usn = f"{college_code}{year}{branch}001"
    print(f"\n  Sample USN: {sample_usn}")
    confirm = input("  Looks correct? (y/n): ").strip().lower()
    
    if confirm != 'y':
        return get_usn_pattern()
    
    return college_code, year, branch


def get_roll_range():
    print()
    print("-" * 50)
    print("STEP 3: Enter the Roll Number Range")
    print("-" * 50)
    
    while True:
        try:
            start = int(input("  Start roll number (e.g., 1): ").strip())
            end = int(input("  End roll number (e.g., 200): ").strip())
            
            if start > end:
                print("  [!] Start must be less than or equal to end.")
                continue
            if start < 1:
                print("  [!] Start must be at least 1.")
                continue
            
            count = end - start + 1
            print(f"\n  Will process {count} students (roll {start:03d} to {end:03d})")
            confirm = input("  Proceed? (y/n): ").strip().lower()
            
            if confirm == 'y':
                return start, end
        except ValueError:
            print("  [!] Please enter valid numbers.")


def get_reval_choice():
    print()
    print("-" * 50)
    print("STEP 4: Is this a Revaluation Run?")
    print("-" * 50)
    print("  If YES: New marks will be compared with existing records.")
    print("          Only subjects with HIGHER marks will be updated.")
    print("  If NO:  Fresh scrape -- all data will be saved as new.")
    print()
    
    choice = input("  Is this a revaluation run? (y/n): ").strip().lower()
    return choice == 'y'


def main():
    print_banner()
    
    # -- Gather inputs --
    url = get_url()
    college_code, year, branch = get_usn_pattern()
    start_roll, end_roll = get_roll_range()
    is_reval = get_reval_choice()
    
    # -- Generate USNs --
    usns = generate_usns(college_code, year, branch, start_roll, end_roll)
    
    # -- Confirm --
    print()
    print("=" * 50)
    print("  CONFIGURATION SUMMARY")
    print("=" * 50)
    print(f"  URL:       {url}")
    print(f"  Pattern:   {college_code}{year}{branch}XXX")
    print(f"  Range:     {usns[0]} -> {usns[-1]}")
    print(f"  Total:     {len(usns)} students")
    print(f"  Mode:      {'REVALUATION' if is_reval else 'FRESH SCRAPE'}")
    print("=" * 50)
    print()
    
    go = input("  Start scraping? (y/n): ").strip().lower()
    if go != 'y':
        print("Cancelled.")
        return
    
    # ── Run ──
    summary, excel_path = run_batch_and_export(
        url=url,
        usns=usns,
        is_reval=is_reval,
        delay=0.5,
        max_retries=15
    )
    
    # ── Final Report ──
    print()
    print("=" * 50)
    print("  ALL DONE!")
    print("=" * 50)
    if excel_path:
        print(f"  Excel file: {excel_path}")
    print(f"  MongoDB:    vtu_database.results")
    print("="* 50)


if __name__ == "__main__":
    main()
