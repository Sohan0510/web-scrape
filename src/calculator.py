"""
SGPA and CGPA Calculator
========================
Calculates the SGPA and CGPA based on VTU grading system and subject credits.
"""

# Hardcoded credits for 3rd semester for now, to be expanded later.
SUBJECT_CREDITS = {
    # 3rd Semester Core
    "BCS301": 4,
    "BCS302": 4,
    "BCS303": 4,
    "BCS304": 3,
    "BCSL305": 1,
    "BSCK307": 1,
    
    # 3rd Semester Electives (e.g., BCS306A, BCS306B, etc.)
    "BCS306": 3,  # Base code for all BCS306x
    "BCS358": 1,  # Base code for all BCS358x
    
    # 3rd Semester Non-credit courses
    "BNSK359": 0,
    "BPEK359": 0,
    "BYOK359": 0,
    
    # 4th Semester Core
    "BCS401": 3,
    "BCS402": 4,
    "BCS403": 4,
    "BCSL404": 1,
    "BBOC407": 2,
    "BUHK408": 1,
    
    # 4th Semester Electives
    "BCS405": 3,  # Base code for all BCS405x
    "BCS456": 1,  # Base code for all BCS456x
    
    # 4th Semester Non-credit courses
    "BNSK459": 0,
    "BPEK459": 0,
    "BYOK459": 0,
    
    # 5th Semester Core
    "BCS501": 4,
    "BCS502": 4,
    "BCS503": 4,
    "BCSL504": 1,
    "BCS586": 2,
    "BRMK557": 3,
    "BCS508": 1,
    
    # 5th Semester Electives
    "BCS515": 3,  # Base code for all BCS515x
    
    # 5th Semester Non-credit courses
    "BNSK559": 0,
    "BPEK559": 0,
    "BYOK559": 0,

    "BCS601":4,
    "BCS602":4,
    "BCS613A":3,
    "BCS613B":3,
    "BCS613C":3,
    "BCS613D":3,
    "BME654B":3,
    "BCS685":2,
    "BCSL606":1,
    "BAIL657C":1,

    "BNSK659": 0,
    "BPEK659": 0,
    "BYOK659": 0,

}

def get_credits(subject_code):
    """Returns the credits for a given subject code, defaulting to 0 if unknown."""
    code_upper = subject_code.upper()
    
    # Exact match
    if code_upper in SUBJECT_CREDITS:
        return SUBJECT_CREDITS[code_upper]
    
    # Prefix match for 1st/2nd Semester (using base letters)
    if code_upper.startswith("BMATS"): return 4
    if code_upper.startswith("BPHYS") or code_upper.startswith("BCHEM") or code_upper.startswith("BCHES"): return 4
    if code_upper.startswith("BPOPS") or code_upper.startswith("BCEDK"): return 3
    if code_upper.startswith("BESCK"): return 3
    if code_upper.startswith("BETCK") or code_upper.startswith("BPLCK"): return 3
    if code_upper.startswith("BENG") or code_upper.startswith("BPWSK"): return 1
    if code_upper.startswith("BKSKK") or code_upper.startswith("BKBK") or code_upper.startswith("BICOK"): return 1
    if code_upper.startswith("BIDTK") or code_upper.startswith("BSFHK"): return 1

    # Prefix match for 3rd/4th/5th Semester electives
    if code_upper.startswith("BCS306"): return 3
    if code_upper.startswith("BCS358"): return 1
    if code_upper.startswith("BCS405"): return 3
    if code_upper.startswith("BCS456"): return 1
    if code_upper.startswith("BCS515"): return 3
        
    # Return 0 by default so we don't skew the SGPA calculation
    return 0

def get_grade_points(marks):
    """Converts total marks to VTU grade points."""
    if marks >= 90: return 10
    elif marks >= 80: return 9
    elif marks >= 70: return 8
    elif marks >= 60: return 7
    elif marks >= 50: return 6
    elif marks >= 45: return 5
    elif marks >= 40: return 4
    else: return 0

def calculate_sgpa(subjects_dict, target_sem=None):
    """
    Calculates SGPA for a given semester.
    Returns (sgpa, total_credits_considered)
    """
    total_grade_points = 0
    total_credits = 0
    
    for code, sub in subjects_dict.items():
        sem = sub.get("semester", 0)
        if target_sem is not None and sem != target_sem:
            continue
            
        credits = get_credits(code)
        
        # If we don't know the credits, we cannot include it in the SGPA safely
        if credits == 0 and "359" not in code and "459" not in code and "559" not in code:
            # Note: "359", "459", and "559" courses explicitly have 0 credits, so they don't add to total_credits anyway
            continue
            
        # Ignore subjects with F or A status -> Grade points = 0
        if sub.get("status") in ("F", "A"):
            total_credits += credits
            continue
            
        marks = sub.get("total", 0)
        grade_points = get_grade_points(marks)
        
        total_grade_points += (grade_points * credits)
        total_credits += credits
            
    if total_credits == 0:
        return 0.0, 0
        
    sgpa = total_grade_points / total_credits
    return round(sgpa, 2), total_credits

def calculate_cgpa(subjects_dict):
    """
    Calculates overall CGPA across all semesters.
    Returns (cgpa, total_credits_considered)
    """
    return calculate_sgpa(subjects_dict, target_sem=None)
