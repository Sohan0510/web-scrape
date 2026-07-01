import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "vtu_database")

# Default URL — can be overridden at runtime by user input
VTU_RESULT_URL = os.getenv("VTU_RESULT_URL", "")

# Tesseract OCR path
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# Directories
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")

# Ensure directories exist
for d in [EXPORTS_DIR, TEMP_DIR]:
    os.makedirs(d, exist_ok=True)