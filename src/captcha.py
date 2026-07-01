import pytesseract
import cv2
import numpy as np
from src.config import TESSERACT_PATH

# Point Python to Tesseract
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

def clean_image_for_ocr(image_bytes):
    """
    Uses OpenCV to isolate the large CAPTCHA characters from VTU's word-cloud noise.
    
    VTU CAPTCHAs have a distinctive structure:
    - Background: many small random words (NOTES, CAMPUS, PASS, etc.) in various colors
    - Foreground: 6 large bold characters that form the actual CAPTCHA code
    
    Strategy: Isolate characters by their SIZE (large = captcha, small = noise).
    """
    # 1. Convert byte stream to an OpenCV image array
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Failed to decode CAPTCHA image bytes")

    # 2. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Simple binary threshold — the captcha chars are dark on light background
    #    Use a moderate threshold to capture the text
    _, binary = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY_INV)

    # 4. EROSION to remove thin/small noise text
    #    Small noise words have thin strokes that will disappear with erosion.
    #    Large captcha characters have thick strokes that survive erosion.
    erode_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    eroded = cv2.erode(binary, erode_kernel, iterations=1)

    # 5. DILATION to restore the surviving large characters back to readable size
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(eroded, dilate_kernel, iterations=1)

    # 6. Connected component analysis to remove small blobs
    #    Only keep components that are large enough to be captcha characters
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated, connectivity=8)
    
    # Calculate image area for relative sizing
    img_height, img_width = dilated.shape
    min_area = (img_height * img_width) * 0.003  # Min 0.3% of image area
    
    # Create clean output
    cleaned = np.zeros_like(dilated)
    for i in range(1, num_labels):  # Skip background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        height = stats[i, cv2.CC_STAT_HEIGHT]
        
        # Keep only components that are tall enough (at least 40% of image height)
        # and have sufficient area
        if area > min_area and height > img_height * 0.3:
            cleaned[labels == i] = 255

    # 7. Invert: Tesseract prefers black text on white background
    result = cv2.bitwise_not(cleaned)

    # (Debug: Save the cleaned image)
    try:
        cv2.imwrite("temp/debug_cleaned_captcha.png", result)
    except Exception:
        pass

    return result


def solve_captcha(image_bytes):
    """
    Cleans the image, then extracts text using Tesseract OCR.
    Tries multiple preprocessing strategies and picks the best result.
    """
    try:
        # --- Strategy 1: Size-based filtering (primary) ---
        cleaned_img = clean_image_for_ocr(image_bytes)
        
        # VTU captchas are alphanumeric, usually 6 chars long.
        # --psm 7: Treat image as a single text line
        config_line = r'--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        
        text1 = pytesseract.image_to_string(cleaned_img, config=config_line)
        result1 = ''.join(text1.split())
        
        if len(result1) == 6:
            return result1

        # --- Strategy 2: Try with --psm 8 (single word) ---
        config_word = r'--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        text2 = pytesseract.image_to_string(cleaned_img, config=config_word)
        result2 = ''.join(text2.split())
        
        if len(result2) == 6:
            return result2

        # --- Strategy 3: Simple threshold approach (fallback) ---
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, simple_thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
        
        text3 = pytesseract.image_to_string(simple_thresh, config=config_word)
        result3 = ''.join(text3.split())
        
        if len(result3) == 6:
            return result3

        # Return the longest reasonable result from any strategy
        candidates = [result1, result2, result3]
        candidates = [c for c in candidates if c]  # Remove empty
        
        if candidates:
            # Prefer the one closest to 6 chars
            candidates.sort(key=lambda x: abs(len(x) - 6))
            return candidates[0]
        
        return ""
        
    except Exception as e:
        print(f"[!] OCR Error: {e}")
        return ""