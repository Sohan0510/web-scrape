# VTU Result Scraper 🎓

A full-stack tool to **automatically scrape, store, and export** student exam results from the VTU (Visvesvaraya Technological University) results portal. It bypasses CAPTCHAs using computer vision, stores results into MongoDB, calculates SGPA/CGPA, and exports everything into clean, professionally formatted Excel reports.

---

## ✨ Features

| Feature                      | Description                                                                                                                                           |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Automated CAPTCHA Bypass** | Uses OpenCV image processing + Tesseract OCR to solve VTU CAPTCHAs automatically — no manual typing needed.                                           |
| **Bulk Scraping**            | Generate a range of USNs (e.g., `1RF23CS001` to `1RF23CS200`) and scrape the entire batch in one go with automatic retry rounds.                      |
| **Revaluation Mode**         | Compare revaluation marks with existing records — only updates subjects where marks have improved. Tracks old vs. new marks side-by-side.             |
| **Student Lookup Portal**    | A clean, public-facing page where students can search their USN to view their marks, SGPA, and CGPA — no login required.                              |
| **Admin Dashboard**          | A separate admin interface with tabs for scraping, viewing all results, searching students, and a CGPA leaderboard.                                   |
| **SGPA & CGPA Calculation**  | Automatically calculates semester-wise SGPA and cumulative CGPA based on VTU's credit and grading system.                                             |
| **Excel Reports**            | Download professionally formatted `.xlsx` reports with multiple sheets: Summary, Detailed Marks, Per-Semester breakdowns, and Subject-wise Analytics. |
| **Fully Dockerized**         | Everything (Python backend, Vite frontend, MongoDB, Tesseract OCR) runs with a single `docker-compose up` command.                                    |

---

## 🏗️ Architecture

```
┌──────────────────┐       ┌──────────────────────┐       ┌──────────────┐
│   Frontend       │       │   Backend (FastAPI)   │       │   MongoDB    │
│   (Vite + JS)    │──────▶│   Port 8000           │──────▶│   Port 27017 │
│   Port 80        │  API  │                       │       │              │
│   Nginx reverse  │       │ ┌──────────────────┐  │       └──────────────┘
│   proxy → :8000  │       │ │ Scraper Engine   │  │
└──────────────────┘       │ │  ├─ captcha.py   │  │
                           │ │  ├─ scraper.py   │  │
                           │ │  └─ batch_runner │  │
                           │ ├──────────────────┤  │
                           │ │ Calculator       │  │
                           │ │  └─ SGPA / CGPA  │  │
                           │ ├──────────────────┤  │
                           │ │ Exporter         │  │
                           │ │  └─ Excel (.xlsx)│  │
                           │ └──────────────────┘  │
                           └──────────────────────┘
```

### Backend Modules (`src/`)

| Module            | Purpose                                                                                                                          |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `scraper.py`      | Fetches VTU result pages, handles CAPTCHA solving, and parses HTML (supports both regular and revaluation formats).              |
| `captcha.py`      | Uses OpenCV (erosion, dilation, connected component analysis) to clean noisy CAPTCHA images, then reads them with Tesseract OCR. |
| `batch_runner.py` | Orchestrates batch scraping of multiple USNs with automatic retry rounds and progress callbacks.                                 |
| `database.py`     | MongoDB operations — saves new records, merges subjects across semesters, and handles revaluation mark comparisons.              |
| `calculator.py`   | Calculates SGPA and CGPA using VTU's credit-based grading system with hardcoded credit mappings for Semesters 1–5.               |
| `exporter.py`     | Generates multi-sheet Excel reports with formatting, color-coded pass/fail, topper highlighting, and subject-wise analytics.     |
| `config.py`       | Loads environment variables and sets up directory paths.                                                                         |

---

## 🛠️ Prerequisites

You only need **Docker** installed:

1. [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Make sure Docker Desktop is running.

That's it. No need to install Python, Node.js, MongoDB, or Tesseract manually.

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/vtu-project.git
cd vtu-project
```

### 2. Start the application

```bash
docker-compose up -d --build
```

> The first run will take a few minutes to download images and build containers. Subsequent starts are fast.

### 3. Open in your browser

| Service                   | URL                                                      |
| ------------------------- | -------------------------------------------------------- |
| **Student Portal**        | [http://localhost](http://localhost)                     |
| **Admin Dashboard**       | [http://localhost/urmom](http://localhost/urmom)         |
| **API Docs (Swagger)**    | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **MongoDB** (for Compass) | `mongodb://localhost:27017/`                             |

---

## 📖 Usage Guide

### Scraping Results (Admin Dashboard)

1. Open the **Admin Dashboard** at `http://localhost/urmom`
2. Go to the **Scrape** tab
3. Fill in the details:
   - **VTU Result URL** — Paste the direct link to the VTU result page (e.g., `https://results.vtu.ac.in/D25J26Ecbcs/index.php`)
   - **College Code** — e.g., `1RF`
   - **Year** — e.g., `23`
   - **Branch** — e.g., `CS`
   - **Roll Range** — e.g., `1` to `200`
4. Toggle **Revaluation Mode** if scraping revaluation results
5. Click **Start Scraping**
6. Watch the live progress bar and log as each student is processed
7. Once complete, click **Download Excel Report**

### Student Result Lookup

1. Open [http://localhost](http://localhost)
2. Enter a USN (e.g., `1RF22CS024`)
3. View marks with SGPA and CGPA, filterable by semester

---

---

## ⚙️ Environment Variables

Out of the box, the Dockerized setup requires **zero configuration**. The `docker-compose.yml` comes pre-configured with sensible defaults.

If you want to connect to an **external MongoDB instance** (e.g., MongoDB Atlas) instead of the built-in Docker container:

1. Copy `.env.example` to `.env`
2. Set your connection string:
   ```env
   MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=<AppName>
   ```

---

## 🛑 Stopping the Application

```bash
# Stop all containers (data is preserved)
docker-compose down

# Stop AND delete all saved data
docker-compose down -v
```

---

## 📁 Project Structure

```
vtu-project/
├── api/
│   └── main.py              # FastAPI application — all API routes
├── src/
│   ├── scraper.py            # VTU page fetcher + HTML parser
│   ├── captcha.py            # CAPTCHA image cleaning + OCR
│   ├── batch_runner.py       # Batch scraping orchestrator
│   ├── database.py           # MongoDB CRUD operations
│   ├── calculator.py         # SGPA & CGPA calculation
│   ├── exporter.py           # Excel report generator
│   └── config.py             # Environment variable loader
├── frontend/
│   ├── src/
│   │   ├── main.js           # Admin dashboard (Scrape/Results/Find/Leaderboard)
│   │   ├── student.js        # Public student lookup portal
│   │   ├── style.css         # Admin dashboard styles
│   │   └── student.css       # Student portal styles
│   ├── nginx.conf            # Nginx config (serves static + proxies API)
│   ├── Dockerfile            # Multi-stage build: Vite → Nginx
│   └── package.json
├── run.py                    # Interactive CLI scraper (alternative to web UI)
├── Dockerfile                # Backend: Python + Tesseract OCR
├── docker-compose.yml        # Full stack orchestration
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
└── exports/                  # Downloaded Excel reports saved here
```

---

## 📊 Excel Report Sheets

Each exported Excel file contains the following sheets:

| Sheet                    | Contents                                                                                                                                                  |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Summary**              | One row per student — USN, name, pass/fail count, grand total, percentage, SGPA, CGPA, overall status. Includes class statistics and topper highlighting. |
| **Detailed Marks**       | One row per subject per student, grouped by semester. Includes old/new marks for revaluation comparisons.                                                 |
| **Sem N** (per semester) | Filtered view of a single semester with per-semester pass rate statistics.                                                                                |
| **Analytics**            | Subject-wise analysis — pass percentage, average marks, highest/lowest scores per subject.                                                                |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is for educational purposes. Use responsibly and in accordance with VTU's terms of service.
