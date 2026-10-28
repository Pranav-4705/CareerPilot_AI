# CareerPilot AI

> **CareerPilot AI** is an autonomous recruitment intelligence and candidate career preparation platform. It provides deterministic resume parsing, structured entity extraction, 5-component ATS benchmarking, version-isolated resume management, and 4-component resume-to-job matching with prioritized skill gap insights. This platform empowers job seekers with data-driven insights to optimize their resumes for ATS systems and prepare effectively for technical interviews.

---

## 🎯 Core Capabilities

- **🔐 Secure Candidate Authentication**: Stateless JWT Bearer token authentication with bcrypt password hashing and user-scoped data isolation.
- **📄 Dual-Format Resume Parsing**: Deterministic local extraction from `.pdf` and `.docx` documents using PyMuPDF and python-docx with binary validation and 5 MB size enforcement.
- **🔍 Structured Entity Extraction**: Deterministic extraction of technical skills (canonical taxonomy), work experience timeline, education degrees, technical projects, and certifications.
- **⚡ 5-Component ATS Scoring**: Explainable 0–100 ATS scoring benchmark across Section Structure (20%), Skills Coverage (25%), Keyword Quality (20%), Experience Depth (20%), and Readability & Formatting (15%).
- **📚 Resume Version Management**: Multi-version tracking (`v1`, `v2`, `v3`) per candidate, atomic active version designation, automatic promotion upon deletion, and version-isolated analysis history.
- **🎯 Job Description Intelligence**: Normalization and structured extraction of required skills, experience thresholds, education qualifications, and core responsibilities from raw job postings.
- **📊 4-Component Resume-to-Job Matching**: Deterministic, transparent weighted matching formula:
  $$\text{Match Score} = 0.50 \times \text{Skills} + 0.20 \times \text{Experience} + 0.10 \times \text{Education} + 0.20 \times \text{Responsibilities}$$
- **💡 Candidate Gap Insights & Recommendations**: Prioritized missing skills (`High`, `Medium`, `Low`), 4-state experience & education evaluations (`meets`, `does_not_meet`, `unknown`, `not_specified`), and actionable severity-graded improvements.
- **🎤 AI-Powered Technical Interview Practice**: Resume-aware dynamic technical interview powered by Google Gemini (with deterministic local fallback). Dynamically deep dives into candidate projects, claimed technologies, architectural trade-offs, and debugging edge cases with instant answer scoring, constructive feedback, and final summary report.

---

## 🏗️ Architecture & Technology Stack

### Tech Stack

#### Backend
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) - Modern, high-performance Python web framework
- **Language**: Python 3.11+
- **Database**: SQLAlchemy ORM with support for PostgreSQL/SQLite
- **Authentication**: JWT (JSON Web Tokens) with bcrypt password hashing
- **Document Parsing**: [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF, [python-docx](https://python-docx.readthedocs.io/) for DOCX
- **AI/ML**: [Google Gemini API](https://ai.google.dev/), [SentenceTransformers](https://www.sbert.net/) for local embeddings
- **Testing**: Pytest with 81 automated tests

#### Frontend
- **Framework**: [Next.js 15](https://nextjs.org/) with App Router
- **Language**: TypeScript
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **Real-time**: [LiveKit Client](https://docs.livekit.io/) for interview functionality
- **State Management**: React Context API

#### DevOps
- **Containerization**: Docker & Docker Compose
- **Version Control**: Git

### Project Structure

```
CareerPilot AI (Monorepo)
├── backend/                       # FastAPI Python 3.11+ Service
│   ├── app/
│   │   ├── api/v1/endpoints/      # Route controllers (auth, resumes, jobs, interviews, health)
│   │   ├── core/                  # Security (JWT, bcrypt), Database session, Config
│   │   ├── models/                # SQLAlchemy models (User, Resume, ResumeAnalysis, JobDescription, JobMatch, TechnicalInterview)
│   │   ├── schemas/               # Pydantic schemas (Job, Resume, ATS, Insights, Interview, Auth)
│   │   └── services/              # Processing & intelligence engines
│   │       ├── parser_service.py          # PyMuPDF & python-docx extraction
│   │       ├── extractor_service.py       # Entity & skills extraction
│   │       ├── ats_service.py             # 5-component ATS scoring
│   │       ├── job_service.py             # Job normalization & requirement extraction
│   │       ├── matching_service.py        # 4-component weighted matching engine
│   │       ├── match_insights_service.py  # Prioritized gap analysis & recommendations
│   │       ├── gemini_service.py          # Google Gemini API & fallback engine
│   │       ├── technical_interview_service.py # Dynamic interview turn & state engine
│   │       └── embedding_service.py       # SentenceTransformers local embeddings
│   ├── tests/                     # 81 automated pytest tests
│   └── requirements.txt
└── frontend/                      # Next.js 15 (App Router) + TypeScript + Tailwind CSS
    └── src/
        ├── app/
        │   ├── page.tsx                   # Public landing page
        │   ├── login/ & register/         # Authenticated credentials workflow
        │   ├── dashboard/                 # Active Resume Workspace & History timeline
        │   ├── resume/                    # Resume upload with drag-and-drop
        │   ├── resume/[id]/analysis/      # Structured entity explorer
        │   ├── resume/[id]/ats/           # Visual ATS breakdown & recommendations
        │   ├── jobs/                      # Target jobs workspace & creation form
        │   ├── jobs/[id]/                 # Job details, extracted requirements & resume selector
        │   ├── jobs/[id]/match/           # 4-component match score, skill gaps & insights
        │   ├── interviews/technical/      # Technical Interview workspace & history
        │   └── interviews/technical/[id]/ # Real-time interview session & completion summary
        ├── context/AuthContext.tsx        # Client authentication state & session persistence
        └── lib/api.ts                     # Strongly typed API client
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Node.js**: v18+ (tested on Node v20/v24)
- **Python**: 3.10+ (tested on Python 3.11)
- **PostgreSQL** or local **SQLite** (SQLite is default if `DATABASE_URL` is omitted)

---

### 1. Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate Python virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (optional, defaults provided)
cp .env.example .env
```

#### Environment Variables (Backend)
Create a `.env` file in the `backend/` directory with the following variables:

```env
# Database (defaults to SQLite if not specified)
DATABASE_URL=sqlite:///./careerpilot.db
# For PostgreSQL: postgresql://user:password@localhost:5432/careerpilot

# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google Gemini API (optional - has fallback engine)
GEMINI_API_KEY=your-gemini-api-key

# File Upload
MAX_UPLOAD_SIZE=5242880  # 5MB in bytes
```

```bash
# 5. Start FastAPI development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Frontend Setup

```bash
# 1. Navigate to frontend directory in a separate terminal
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env.local
```

#### Environment Variables (Frontend)
Create a `.env.local` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
# 4. Start Next.js development server
npm run dev
```

- **Web Application**: [http://localhost:3000](http://localhost:3000)

---

### 3. Docker Setup (Alternative)

Run the entire application stack using Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d --build

# Stop all services
docker-compose down
```

---

## 🔄 End-to-End Candidate Workflow

1. **Register / Login**: Create a candidate profile; receive a secure JWT token.
2. **Upload Resume**: Upload PDF or DOCX file ($\le 5\text{ MB}$) on `/resume`.
3. **Parse Text**: Extract raw text deterministically with PyMuPDF/python-docx.
4. **Structured Analysis**: Extract skills, education, experience, projects, and certifications on `/resume/[id]/analysis`.
5. **Evaluate ATS Score**: Benchmark resume against ATS parsing criteria and review component scores on `/resume/[id]/ats`.
6. **Manage Versions**: Upload new resume iterations, toggle active version, or delete old versions on `/dashboard`.
7. **Create Target Job**: Paste job description and normalize requirements on `/jobs`.
8. **Match Resume to Job**: Select any analyzed resume version and calculate 4-component compatibility score.
9. **Review Gap Insights**: Inspect matched vs missing skills, prioritized gap categories, 4-state experience/education evaluations, and actionable improvement recommendations on `/jobs/[id]/match`.
10. **Practice Technical Interview**: Start an adaptive, resume-aware interview session on `/interviews/technical`. Answer questions, review instant feedback on accuracy, relevance, and depth, and receive a final performance breakdown with strengths and improvement areas.

---

## 🧪 Automated Testing & Verification

### Backend Automated Test Suite
```bash
cd backend
.venv\Scripts\pytest -v
```
- **81 Tests Passing** covering Auth, Resumes, Parser, Extraction, ATS Scoring, Versioning, Job Intelligence, 4-Component Matching, Match Insights, Gemini Integration, and Technical Interviews.

### Frontend Production Build
```bash
cd frontend
npm run build
```
- **11 Next.js Static & Dynamic Routes** compiling cleanly with 0 TypeScript and 0 linting errors.

---

## 🔒 Security & Data Isolation Guarantees

- **Stateless Authentication**: Protected API endpoints enforce JWT verification in `Authorization: Bearer <token>`.
- **Strict Ownership**: Candidates can only access, parse, analyze, match, or delete their own resumes and jobs. Cross-user attempts yield `404 Not Found`.
- **Deterministic & Safe**: Core parsing, extraction, ATS scoring, and matching operate locally. Optional Gemini integration has a deterministic local fallback.
- **Fail-Safe Integrity**: Deleting a resume safely purges its file on disk, preserves remaining versions, and automatically promotes the newest remaining version to active.
- **Input Validation**: Binary validation, file type checking, and 5 MB size enforcement for uploads.
- **Password Security**: bcrypt hashing for secure password storage.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📧 Contact

For questions or support, please open an issue on the [GitHub repository](https://github.com/Pranav-4705/CareerPilot_AI).
