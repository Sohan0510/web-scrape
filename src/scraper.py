"""
VTU Result Page Scraper
========================
Handles fetching and parsing of VTU result pages.
Supports both regular and revaluation result formats.

Regular results use div-based tables with 6 columns.
Revaluation results use div-based tables with 9 columns.
"""

import requests
from bs4 import BeautifulSoup
import urllib3
from urllib.parse import urljoin
from src.captcha import solve_captcha

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _get_result_url(base_url):
    """Derives the result submission URL from the base URL."""
    base = base_url.rsplit('/', 1)[0]
    return f"{base}/resultpage.php"


def parse_result_page(result_soup):
    """
    Parses VTU result page HTML — handles BOTH formats:
    
    1) Regular results:  div-based tables (divTableBody/divTableRow/divTableCell)
       Columns: Subject Code, Subject Name, Internal, External, Total, Result
       
    2) Revaluation results:  div-based tables with 9 columns:
       Subject Code, Subject Name, Internal Marks, Old Marks, Old Result,
       RV Marks, RV Result, Final Marks, Final Result
    
    Returns:
        tuple: (student_name, subjects_dict, grand_total)
    """
    student_name = _parse_student_name(result_soup)
    
    is_reval_page = _is_reval_format(result_soup)
    
    if is_reval_page:
        subjects, grand_total = _parse_reval_table(result_soup)
    else:
        subjects, grand_total = _parse_regular_divtable(result_soup)

    return student_name, subjects, grand_total


def _parse_student_name(soup):
    """
    Extracts student name from VTU result page.
    Handles multiple possible HTML structures:
      - <td>Student Name</td><td>: JOHN DOE</td>
      - Div-based info sections
      - Table-based info sections
    """
    def clean_name(n):
        n = n.lstrip(':').strip()
        # If it accidentally captured the next label, clean it up
        for invalid_word in ['Semester', 'Father', 'Mother', 'USN']:
            if invalid_word.lower() in n.lower():
                n = n[:n.lower().index(invalid_word.lower())].strip()
                n = n.rstrip(':').strip()
        return n

    # Method 0: New VTU divTableCell-based lookup (2026+ format)
    # Student info is in divTableBody -> divTableRow -> divTableCell pairs
    name_cells = soup.find_all('div', class_='divTableCell')
    for i, cell in enumerate(name_cells):
        cell_text = cell.get_text(strip=True)
        if cell_text == 'Student Name':
            # The name value should be the next sibling divTableCell
            next_cell = cell.find_next_sibling('div', class_='divTableCell')
            if next_cell:
                name = clean_name(next_cell.get_text(strip=True))
                if name: return name

    # Method 1: Standard td-based lookup
    name_td = soup.find(
        lambda tag: tag.name == 'td' and 'Student Name' in tag.get_text()
    )
    if name_td:
        # Check if name is within the same td: <td>Student Name : JOHN DOE</td>
        text = name_td.get_text(separator=' ', strip=True)
        if ':' in text:
            parts = text.split(':', 1)
            if len(parts) > 1 and parts[1].strip():
                name = clean_name(parts[1])
                if name: return name

        # Look at the next sibling td
        name_value_td = name_td.find_next_sibling('td')
        if name_value_td:
            name = clean_name(name_value_td.get_text(separator=' ', strip=True))
            if name: return name

    # Method 2: Look for td with pattern near "Student Name" text
    all_tds = soup.find_all('td')
    for i, td in enumerate(all_tds):
        text = td.get_text(separator=' ', strip=True)
        if 'student name' in text.lower():
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) > 1 and parts[1].strip():
                    name = clean_name(parts[1])
                    if name: return name
            
            # Check next td
            if i + 1 < len(all_tds):
                name = clean_name(all_tds[i + 1].get_text(separator=' ', strip=True))
                if name: return name
    
    # Method 3: Search entire page text
    page_text = soup.get_text(separator='  ', strip=True)
    import re
    match = re.search(r'Student\s*Name\s*[:\-]\s*(.+?)(?:\s\s|$)', page_text)
    if match:
        name = clean_name(match.group(1))
        if name: return name
        
    # Method 4: Div-based layout lookup
    # VTU sometimes uses divs for the student info table
    divs = soup.find_all('div')
    for i, div in enumerate(divs):
        text = div.get_text(separator=' ', strip=True)
        if text.lower() == 'student name' or text.lower() == 'student name :':
            if i + 1 < len(divs):
                name = clean_name(divs[i + 1].get_text(separator=' ', strip=True))
                if name: return name

    return ""


def _is_reval_format(soup):
    """
    Detects if the page is a revaluation result page.
    Reval pages have headers like 'Final Marks' / 'RV Marks' / 'Old Marks'.
    """
    page_text = soup.get_text()
    if 'Final Marks' in page_text or 'RV Marks' in page_text:
        return True
    # Check divTableCell headers
    header_cells = soup.find_all('div', class_='divTableCell')
    for cell in header_cells:
        cell_text = cell.get_text(strip=True)
        if cell_text in ('Final Marks', 'RV Marks', 'Old Marks', 'Final Result', 'RV Result'):
            return True
    return False


def _parse_regular_divtable(soup):
    """
    Parses regular VTU results using CSS div-based tables.
    Uses header-based column mapping so it adapts to any number of columns.
    Supports both old 6-col format and new 7-col format (with 'Announced / Updated on').
    """
    subjects = {}
    grand_total = 0

    table_bodies = soup.find_all('div', class_='divTableBody')

    for table_body in table_bodies:
        rows = table_body.find_all('div', class_='divTableRow')
        
        # Try to find a header row to build a column map
        header_row_idx = -1
        col_map = {}
        
        for idx, row in enumerate(rows):
            cells = row.find_all('div', class_='divTableCell')
            row_texts = [c.get_text(strip=True).lower() for c in cells]
            if any('subject code' in t for t in row_texts):
                for i, h in enumerate(row_texts):
                    if 'subject code' in h:
                        col_map['code'] = i
                    elif 'subject name' in h:
                        col_map['name'] = i
                    elif 'internal' in h:
                        col_map['internal'] = i
                    elif 'external' in h:
                        col_map['external'] = i
                    elif h == 'total':
                        col_map['total'] = i
                    elif h == 'result':
                        col_map['result'] = i
                header_row_idx = idx
                break
        
        # If we found a header row, parse data rows using the column map
        if header_row_idx != -1 and 'code' in col_map:
            data_rows = rows[header_row_idx + 1:]
            for row in data_rows:
                cells = row.find_all('div', class_='divTableCell')
                if len(cells) < 3:
                    continue
                
                def _cell(key):
                    idx = col_map.get(key)
                    if idx is not None and idx < len(cells):
                        return cells[idx].get_text(strip=True)
                    return ''
                
                sub_code = _cell('code')
                if not sub_code or sub_code.lower() == 'subject code' or '->' in sub_code:
                    continue
                
                sub_name = _cell('name')
                internals_text = _cell('internal')
                externals_text = _cell('external')
                total_text = _cell('total')
                result_status = _cell('result')
                
                internals = int(internals_text) if internals_text.isdigit() else 0
                externals = int(externals_text) if externals_text.isdigit() else 0
                total = int(total_text) if total_text.isdigit() else 0
                
                subjects[sub_code] = {
                    "name": sub_name,
                    "internals": internals,
                    "externals": externals,
                    "total": total,
                    "status": result_status,
                    "semester": _extract_semester(sub_code)
                }
                grand_total += total
        else:
            # Fallback: no header found, try positional parsing (old 6-col format)
            for row in rows:
                style = row.get('style', '')
                if 'font-weight' in style and 'bold' in style:
                    continue
                
                cells = row.find_all('div', class_='divTableCell')
                
                if len(cells) >= 6:
                    sub_code = cells[0].get_text(strip=True)
                    sub_name = cells[1].get_text(strip=True)
                    internals_text = cells[2].get_text(strip=True)
                    externals_text = cells[3].get_text(strip=True)
                    total_text = cells[4].get_text(strip=True)
                    result_status = cells[5].get_text(strip=True)
                    
                    if not sub_code or sub_code == 'Subject Code' or '->' in sub_code:
                        continue
                    
                    internals = int(internals_text) if internals_text.isdigit() else 0
                    externals = int(externals_text) if externals_text.isdigit() else 0
                    total = int(total_text) if total_text.isdigit() else 0
                    
                    subjects[sub_code] = {
                        "name": sub_name,
                        "internals": internals,
                        "externals": externals,
                        "total": total,
                        "status": result_status,
                        "semester": _extract_semester(sub_code)
                    }
                    grand_total += total

    return subjects, grand_total


def _parse_reval_divtable(soup):
    """
    Parses VTU revaluation result pages that use CSS div-based tables.
    
    Reval divTable columns (9):
      Subject Code | Subject Name | Internal Marks | Old Marks | Old Result |
      RV Marks | RV Result | Final Marks | Final Result
    """
    subjects = {}
    grand_total = 0

    table_bodies = soup.find_all('div', class_='divTableBody')

    for table_body in table_bodies:
        rows = table_body.find_all('div', class_='divTableRow')

        header_row_idx = -1
        col_map = {}

        for idx, row in enumerate(rows):
            cells = row.find_all('div', class_='divTableCell')
            row_texts = [c.get_text(strip=True).lower() for c in cells]
            if any('subject' in t for t in row_texts):
                for i, h in enumerate(row_texts):
                    if 'subject code' in h:
                        col_map['code'] = i
                    elif 'subject name' in h:
                        col_map['name'] = i
                    elif 'internal' in h:
                        col_map['internal'] = i
                    elif 'old marks' in h or 'old mark' in h:
                        col_map['old_marks'] = i
                    elif 'old result' in h:
                        col_map['old_result'] = i
                    elif 'rv marks' in h or 'rv mark' in h or 'reval mark' in h:
                        col_map['rv_marks'] = i
                    elif 'rv result' in h or 'reval result' in h:
                        col_map['rv_result'] = i
                    elif 'final marks' in h or 'final mark' in h:
                        col_map['final_marks'] = i
                    elif 'final result' in h:
                        col_map['final_result'] = i
                header_row_idx = idx
                break

        if header_row_idx == -1 or 'code' not in col_map:
            continue

        data_rows = rows[header_row_idx + 1:]

        for row in data_rows:
            cells = row.find_all('div', class_='divTableCell')
            if len(cells) < 3:
                continue

            def _cell(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(cells):
                    return cells[idx].get_text(strip=True)
                return ''

            sub_code = _cell('code')
            if not sub_code or sub_code.lower() == 'subject code' or '->' in sub_code:
                continue

            sub_name = _cell('name')
            internals_text = _cell('internal')
            final_marks_text = _cell('final_marks')
            final_result = _cell('final_result')
            old_marks_text = _cell('old_marks')
            rv_marks_text = _cell('rv_marks')
            old_result = _cell('old_result')
            rv_result = _cell('rv_result')

            internals = int(internals_text) if internals_text.isdigit() else 0

            if final_marks_text and final_marks_text.isdigit():
                externals = int(final_marks_text)
                total = internals + externals
                status = final_result if final_result else 'P'
            else:
                continue

            subject_entry = {
                "name": sub_name,
                "internals": internals,
                "externals": externals,
                "total": total,
                "status": status,
                "semester": _extract_semester(sub_code)
            }

            if old_marks_text and old_marks_text.isdigit():
                old_ext = int(old_marks_text)
                subject_entry["old_marks"] = old_ext
                subject_entry["old_total"] = internals + old_ext
                subject_entry["old_result"] = old_result
            if rv_marks_text and rv_marks_text.isdigit():
                rv_ext = int(rv_marks_text)
                subject_entry["rv_marks"] = rv_ext
                subject_entry["rv_total"] = internals + rv_ext
                subject_entry["rv_result"] = rv_result

            subjects[sub_code] = subject_entry
            grand_total += total

    return subjects, grand_total


def _parse_reval_table(soup):
    """
    Parses VTU revaluation result pages.
    Tries div-based table first (actual VTU format), then HTML <table> fallback.
    """
    # Try div-based table first (actual VTU format)
    subjects, grand_total = _parse_reval_divtable(soup)
    if subjects:
        return subjects, grand_total

    # Fallback: standard HTML <table>
    subjects = {}
    grand_total = 0

    tables = soup.find_all('table')
    
    for table in tables:
        all_rows = table.find_all('tr')
        header_row_idx = -1
        headers = []
        
        for idx, row in enumerate(all_rows):
            cells = row.find_all(['th', 'td'])
            row_texts = [c.get_text(strip=True).lower() for c in cells]
            if any('subject' in t for t in row_texts):
                headers = row_texts
                header_row_idx = idx
                break
        
        if header_row_idx == -1:
            continue
        
        col_map = {}
        for i, h in enumerate(headers):
            if 'subject code' in h:
                col_map['code'] = i
            elif 'subject name' in h:
                col_map['name'] = i
            elif 'internal' in h:
                col_map['internal'] = i
            elif 'old marks' in h or 'old mark' in h:
                col_map['old_marks'] = i
            elif 'old result' in h:
                col_map['old_result'] = i
            elif 'rv marks' in h or 'rv mark' in h or 'reval mark' in h:
                col_map['rv_marks'] = i
            elif 'rv result' in h or 'reval result' in h:
                col_map['rv_result'] = i
            elif 'final marks' in h or 'final mark' in h:
                col_map['final_marks'] = i
            elif 'final result' in h:
                col_map['final_result'] = i
            elif 'external' in h:
                col_map['external'] = i
            elif 'total' in h:
                col_map['total'] = i
            elif 'result' in h and 'old' not in h and 'rv' not in h and 'final' not in h:
                col_map['result'] = i
        
        if 'code' not in col_map:
            continue
        
        rows = all_rows[header_row_idx + 1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            
            def _cell(key):
                idx = col_map.get(key)
                if idx is not None and idx < len(cells):
                    return cells[idx].get_text(strip=True)
                return ''
            
            sub_code = _cell('code')
            if not sub_code or sub_code.lower() == 'subject code' or '->' in sub_code:
                continue
            
            sub_name = _cell('name')
            internals_text = _cell('internal')
            
            final_marks_text = _cell('final_marks')
            final_result = _cell('final_result')
            old_marks_text = _cell('old_marks')
            rv_marks_text = _cell('rv_marks')
            old_result = _cell('old_result')
            rv_result = _cell('rv_result')
            
            external_text = _cell('external')
            total_text = _cell('total')
            plain_result = _cell('result')
            
            internals = int(internals_text) if internals_text.isdigit() else 0
            
            if final_marks_text and final_marks_text.isdigit():
                externals = int(final_marks_text)
                total = internals + externals
                status = final_result or 'P'
            elif total_text and total_text.isdigit():
                total = int(total_text)
                externals = int(external_text) if external_text.isdigit() else 0
                status = plain_result or 'P'
            else:
                continue
            
            subject_entry = {
                "name": sub_name,
                "internals": internals,
                "externals": externals,
                "total": total,
                "status": status,
                "semester": _extract_semester(sub_code)
            }
            
            if old_marks_text and old_marks_text.isdigit():
                old_ext = int(old_marks_text)
                subject_entry["old_marks"] = old_ext
                subject_entry["old_total"] = internals + old_ext
                subject_entry["old_result"] = old_result
            if rv_marks_text and rv_marks_text.isdigit():
                rv_ext = int(rv_marks_text)
                subject_entry["rv_marks"] = rv_ext
                subject_entry["rv_total"] = internals + rv_ext
                subject_entry["rv_result"] = rv_result
            
            subjects[sub_code] = subject_entry
            grand_total += total

    return subjects, grand_total


def _extract_semester(subject_code):
    """
    Extracts semester number from a VTU subject code.
    VTU codes: <LETTERS><SEM_DIGIT><REST>  e.g. BCS501 -> 5
    """
    for char in subject_code:
        if char.isdigit():
            return int(char)
    return 0


def fetch_student_result(usn, url, max_retries=15):
    """
    Fetches a single student's result from the VTU portal.
    
    Returns:
        dict with keys: usn, name, subjects, grand_total, attempts
        OR dict with key: error
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Referer': url,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })

    result_url = _get_result_url(url)

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=15, verify=False)
            soup = BeautifulSoup(response.text, 'html.parser')

            captcha_img_tag = soup.find('img', alt="CAPTCHA code")
            if not captcha_img_tag:
                continue
                
            captcha_src = captcha_img_tag.get('src', '')
            captcha_src = captcha_src.replace("&amp;", "&")
            captcha_url = urljoin(url, captcha_src)

            captcha_response = session.get(captcha_url, timeout=10, verify=False)
            
            if len(captcha_response.content) < 100:
                continue
            
            captcha_text = solve_captcha(captcha_response.content)
            
            if len(captcha_text) != 6:
                continue

            token_tag = soup.find('input', {'name': 'Token'})
            token = token_tag['value'] if token_tag else ''

            payload = {
                'lns': usn,
                'captchacode': captcha_text,
                'Token': token
            }

            post_response = session.post(result_url, data=payload, verify=False, timeout=15)
            result_soup = BeautifulSoup(post_response.text, 'html.parser')

            # Check for student name in <td> (old format) or <div> (new format)
            name_td = result_soup.find(
                lambda tag: tag.name == 'td' and 'Student Name' in tag.get_text()
            )
            name_div = result_soup.find(
                lambda tag: tag.name == 'div' and tag.get('class') and 'divTableCell' in tag.get('class', []) and 'Student Name' in tag.get_text() and len(tag.get_text()) < 50
            )
            has_student_info = name_td or name_div
            
            if not has_student_info:
                page_text = post_response.text
                if "not applied for reval" in page_text or "reval results are awaited" in page_text:
                    return {
                        "usn": usn,
                        "name": "",
                        "subjects": {},
                        "grand_total": 0,
                        "attempts": attempt,
                        "reval_status": "Not Applied"
                    }
                if ("University Seat Number is not available" in page_text
                    or "not available or Invalid" in page_text
                    or "Invalid..!" in page_text):
                    return {"error": f"USN {usn} not found -- not available or Invalid."}
                continue

            student_name, subjects, grand_total = parse_result_page(result_soup)
            is_reval_page = _is_reval_format(result_soup)
            
            return {
                "usn": usn,
                "name": student_name,
                "subjects": subjects,
                "grand_total": grand_total,
                "attempts": attempt,
                "reval_status": "Applied" if is_reval_page else "Regular"
            }

        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.ConnectionError:
            pass
        except Exception as e:
            print(f"   [!] Error for {usn} attempt {attempt}: {e}")

    return {"error": f"Failed to bypass CAPTCHA after {max_retries} attempts for {usn}."}