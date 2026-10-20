# SafePath AI — AI-Powered Personal Safety & Route Planning

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/framework-Flask%203.x-green.svg)](https://flask.palletsprojects.com/)
[![Leaflet](https://img.shields.io/badge/maps-Leaflet%201.9-brightgreen.svg)](https://leafletjs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 16 Passed](https://img.shields.io/badge/tests-16%20passed-success.svg)](https://docs.pytest.org/)

**SafePath AI** is an intelligent, full-stack personal safety and route-planning web application. It combines interactive OpenStreetMap navigation, an explainable community hazard risk-scoring engine, crowd-sourced safety reports, and privacy-conscious emergency assistance into one unified platform.

---

## 🌟 Core Features

### 1. 🧭 Safe Route Finder
- **Interactive Multi-Modal Routing:** Enter an origin and destination to compare Walking, Cycling, or Driving routes.
- **Corridor Safety Scoring (0–100):** Every route alternative is evaluated along a **250-meter safety buffer** against active community-reported hazards.
- **Explainable Factor Breakdown:** Inspect transparent, documented point deductions (e.g. *-12 pts for broken streetlights within 50m*, *-18 pts for isolated passage reports*).
- **Preference Tuning:** Compare routes by **Safest Route** (prioritize highest safety score), **Fastest**, or **Balanced**.
- **Transparent Data Status:** Areas with zero community reports clearly show *"Insufficient Safety Data"* rather than presenting an unverified score as fact.

### 2. 🗺️ Unsafe Area Map
- **Live Community Hazard Markers:** Visual map pins categorized by type:
  - 💡 Broken or non-functional streetlights
  - 👁️ Isolated or poorly monitored areas
  - ⚠️ Road damage and potholes
  - 🛡️ Suspicious activity
  - 🛑 Harassment or threatening behavior
  - 🚧 Blocked roads or unsafe construction
  - ℹ️ Other safety concerns
- **Marker Clustering & Dynamic Filters:** Filter by category, severity (Low, Medium, High), verification status, and timeframe (Last 24h, 7d, 30d, All time).
- **Community Corroboration:** 1-Click "+1 Confirm Hazard" allows community members to verify reports, increasing risk weighting and triggering auto-verification at 3+ confirmations.

### 3. 📢 Report an Unsafe Place
- **Interactive Map Pinning:** Click anywhere on the map or drag the pin to set the exact coordinates with real-time reverse-geocoded address preview.
- **Privacy-Preserving Photo Uploads:** Server-side image processing automatically strips EXIF metadata (camera serials and embedded GPS tags) to protect reporters' privacy.
- **Structured Validation:** Validates coordinates, severity, categories, and description length on both frontend and backend.

### 4. 🚨 Emergency SOS & Revocable Location Sharing
- **1-Click SOS Trigger:** Request GPS location with a 5-second countdown and instant cancellation option.
- **Cryptographic Token Sharing:** Generates a secure, 64-character random token (stored only as a SHA-256 hash) with time-limited expiration.
- **Multi-Channel Dispatch:** One-click Native Share (mobile/desktop), WhatsApp forward, and Native SMS.
- **Instant Revocation:** Deactivate the live sharing link at any moment.
- **Local Emergency Directory:** Quick-dial hotlines (Police 112/911, Medical, Fire, Women's Helpline).

### 5. 👤 User Authentication & Profile
- Secure password hashing using Werkzeug.
- Manage up to 10 personal Trusted Contacts.
- View personal hazard report history and track approval status.
- Account and personal data deletion option for privacy compliance.
- Guest users can freely browse maps, compare routes, and view emergency directories without logging in.

### 6. 🛡️ Admin Moderation & Safety Analytics Center
- **Moderation Queue:** Filter reports by pending, verified, or rejected. Approve, reject, adjust severity, or delete spam reports.
- **Audit Logging:** Every moderation action is recorded with moderator ID and rationale in `ModerationLog`.
- **Analytics Charts:** Category distribution (doughnut chart) and status breakdown (bar chart) powered by Chart.js.

---

## 📐 Explainable Risk-Scoring Engine

SafePath AI rejects opaque neural black boxes for personal route safety. All scores are computed using a documented, explainable weighted scoring model:

$$\text{SafetyScore} = \max\left(5.0, \min\left(100.0, 100 - \sum \left[ \text{BasePenalty} \times \text{SeverityMult} \times \text{ProximityMult} \times \text{RecencyMult} \times \text{VerificationMult} \right] \right)\right)$$

### Factor Multipliers:
1. **Hazard Base Penalty:**
   - Harassment: `24 pts`
   - Suspicious Activity: `20 pts`
   - Isolated Passage: `16 pts`
   - Blocked Road: `14 pts`
   - Broken Streetlights: `12 pts`
   - Road Damage / Potholes: `10 pts`
   - Other Concern: `8 pts`
2. **Severity Multiplier:**
   - High Hazard: `1.6x`
   - Medium Risk: `1.0x`
   - Low Concern: `0.6x`
3. **Proximity Buffer Decay:**
   - `< 50m` (Directly adjacent to route): `1.0x`
   - `50m – 150m` (Nearby connecting lane): `0.65x`
   - `150m – 250m` (Perimeter corridor): `0.35x`
   - `> 250m`: `0.0x` (Ignored)
4. **Recency Decay:**
   - `≤ 3 days`: `1.0x`
   - `4 – 14 days`: `0.8x`
   - `15 – 30 days`: `0.6x`
   - `> 30 days`: `0.4x`
5. **Verification Factor:**
   - Verified by Moderator or 3+ Confirmations: `1.0x – 1.25x`
   - Community Pending: `0.55x`
   - Rejected: `0.0x`

### Score Categorization:
- **80 – 100:** *Lower Reported Risk* (Green)
- **50 – 79:** *Moderate Reported Risk* (Amber)
- **0 – 49:** *Higher Reported Risk* (Red)
- **No data in area:** *Insufficient Safety Data* (Neutral)

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, FontAwesome 6, Google Fonts (Outfit & Inter) |
| **Maps** | Leaflet.js 1.9.4, OpenStreetMap Tiles, Leaflet.markercluster 1.5.3 |
| **Routing & Geocoding** | OSRM (Open Source Routing Machine), Nominatim OpenStreetMap Geocoder, Built-in Offline Simulation Engine |
| **Backend** | Python 3.10+, Flask 3.1, Jinja2 Templates |
| **Database & ORM** | SQLAlchemy, SQLite (default zero-config) / PostgreSQL ready |
| **Authentication** | Flask-Login with secure Werkzeug password hashing |
| **Image Processing** | Pillow (EXIF GPS stripping, thumbnail optimization) |
| **Testing** | pytest (16 automated tests covering auth, hazards, risk scoring, emergency, admin) |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or newer installed.
- Git (optional).

### 2. Installation

Clone or navigate to the project directory:
```bash
cd SafePath_AI
```

Create and activate a virtual environment (optional but recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the sample environment file:
```bash
# Windows PowerShell
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

The default `.env` is pre-configured to run out-of-the-box with SQLite and simulation notification services:
```env
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=safepath_super_secret_session_key_change_in_production_2026
DATABASE_URL=sqlite:///safepath.db
OSRM_BASE_URL=https://router.project-osrm.org
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
SMS_PROVIDER=mock
```

### 4. Database Setup & Realistic Demonstration Seeding

Initialize database tables and seed sample accounts, contacts, and 15 realistic community hazard reports:
```bash
python seed_data.py
```

### 5. Run the Application

Start the Flask development server:
```bash
python app.py
```
Open your web browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## ⚡ Deploying to Vercel

SafePath AI includes complete, production-ready configuration for **Vercel** serverless deployment via `vercel.json` and `api/index.py`.

### 1-Click Import Method:
1. Go to [vercel.com](https://vercel.com) and log in with your GitHub account.
2. Click **"Add New..."** &rarr; **"Project"**.
3. Select your repository: **`Anubhavtiwari254/SafePath_AI`**.
4. In the Project Configuration:
   - **Framework Preset:** Leave as *Other*.
   - **Root Directory:** `./`
5. *(Optional)* Add Environment Variables in the Vercel Dashboard:
   - `SECRET_KEY`: Set to any secure random string.
   - `DATABASE_URL`: *(Optional)* Any PostgreSQL database URI (e.g. Supabase, Neon, Railway). If omitted, SafePath AI automatically uses `/tmp/safepath.db` with auto-seeded demonstration hazards.
   - `SMS_PROVIDER`: `mock` (or `twilio` if you have Twilio credentials).
6. Click **Deploy**. Vercel will install dependencies from `requirements.txt` and launch your live application with a global HTTPS URL!

---

## 🔑 Pre-Configured Demonstration Accounts

| Role | Email | Password | Features Accessible |
|---|---|---|---|
| **Administrator** | `admin@safepath.ai` | `admin123` | Full access: Moderation Queue, Verify/Reject reports, Audit Log, Safety Analytics |
| **Demo User** | `demo@safepath.ai` | `safepath123` | Route Finder, Saved Contacts, Report History, SOS Broadcasting |
| **Guest** | *None required* | *None* | Public maps, Route Finder, Hazard reporting, Emergency hotlines |

*(Both accounts are pre-populated with a 1-click login quick-fill button on the `/login` page).*

---

## 🧪 Running Automated Tests

Run the complete test suite with verbose output:
```bash
pytest -v
```

Expected output:
```text
tests/test_admin.py::test_admin_access_control PASSED
tests/test_admin.py::test_admin_report_moderation PASSED
tests/test_auth.py::test_register_success PASSED
tests/test_auth.py::test_register_duplicate_email PASSED
tests/test_auth.py::test_login_success_and_logout PASSED
tests/test_auth.py::test_login_invalid_credentials PASSED
tests/test_emergency.py::test_activate_and_query_emergency_share PASSED
tests/test_hazards.py::test_submit_hazard_report PASSED
tests/test_hazards.py::test_submit_hazard_invalid_category PASSED
tests/test_hazards.py::test_hazard_confirmation PASSED
tests/test_hazards.py::test_get_hazards_filtering PASSED
tests/test_risk_engine.py::test_haversine_and_distance_calculations PASSED
tests/test_risk_engine.py::test_clean_route_evaluation PASSED
tests/test_risk_engine.py::test_hazard_deduction_in_corridor PASSED
tests/test_risk_engine.py::test_hazard_outside_buffer_ignored PASSED
tests/test_risk_engine.py::test_route_ranking_preferences PASSED

======================= 16 passed in 5.64s =======================
```

---

## 📁 Project Architecture

```text
SafePath_AI/
├── app.py                      # Application factory, blueprints & CLI
├── config.py                   # Central configuration & category definitions
├── seed_data.py                # Database population with demo hazards
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment variables
├── .env                        # Local development environment
├── models/                     # SQLAlchemy database models
│   ├── __init__.py             # Database instance
│   ├── user.py                 # User & TrustedContact models
│   ├── hazard.py               # HazardReport & ReportConfirmation models
│   └── emergency.py            # EmergencyShare & ModerationLog models
├── services/                   # Business logic and external service integrations
│   ├── __init__.py
│   ├── geocoding_service.py    # Nominatim geocoder with fallback coordinates
│   ├── routing_service.py      # OSRM router with resilient simulation fallback
│   ├── risk_engine.py          # Explainable corridor risk calculation & ranking
│   ├── notification_service.py # Multi-channel emergency alert dispatcher
│   └── image_service.py        # Secure image upload & EXIF GPS stripping
├── routes/                     # Blueprint controller modules
│   ├── __init__.py
│   ├── main.py                 # Home, about, dashboard routes
│   ├── auth.py                 # Registration, login, logout, profile
│   ├── route_finder.py         # Route comparison and safety score APIs
│   ├── hazards.py              # Hazard submission, safety map & confirmation
│   ├── emergency.py            # SOS trigger, share token & trusted contacts
│   └── admin.py                # Moderation queue, audit logs & analytics
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Layout with sticky navbar & floating SOS
│   ├── index.html              # Hero section, quick search & feature cards
│   ├── route_finder.html       # Route comparison with Leaflet map
│   ├── safety_map.html         # Fullscreen hazard map with filters
│   ├── report_hazard.html      # Hazard report form with map pin picker
│   ├── emergency.html          # SOS workflow & emergency resources
│   ├── emergency_view.html     # Recipient live location beacon viewer
│   ├── dashboard.html          # User dashboard, contacts & report tracking
│   ├── about.html              # Risk engine explanation & safety disclaimer
│   ├── admin.html              # Admin moderation & Chart.js analytics
│   └── auth/
│       ├── login.html          # Sign in with 1-click demo fill
│       └── register.html       # User registration
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css           # Modern design system & styling
│   ├── js/
│   │   ├── map_common.js       # Leaflet map helpers & popup generators
│   │   ├── route_finder.js     # Route comparison controller
│   │   ├── safety_map.js       # Unsafe Area Map controller
│   │   ├── report_hazard.js    # Map pin picker & photo preview
│   │   ├── emergency.js        # SOS countdown & location share controller
│   │   └── admin.js            # Moderation actions & Chart.js charts
│   └── uploads/                # Photo uploads (EXIF stripped)
├── tests/                      # Automated test suite
│   ├── __init__.py
│   ├── conftest.py             # In-memory test fixtures
│   ├── test_auth.py            # Authentication tests
│   ├── test_hazards.py         # Hazard CRUD & confirmation tests
│   ├── test_risk_engine.py     # Corridor distance & scoring tests
│   ├── test_emergency.py      # SOS token & revocation tests
│   └── test_admin.py          # Admin moderation & audit log tests
└── README.md                   # Project documentation
```

---

## 🔒 Security & Privacy Practices

1. **Password Security:** Passwords hashed using standard PBKDF2/SHA-256 via Werkzeug.
2. **Reporter Anonymity:** Public hazard map markers never disclose personal identities or contact details of submitting users.
3. **EXIF Stripping:** Uploaded photos are stripped of all camera metadata and GPS coordinates using Pillow before being saved.
4. **Hashed Emergency Tokens:** Emergency sharing links use cryptographically random 64-character tokens. Only their SHA-256 hash is persisted in the database.
5. **Time-Limited & Revocable:** Emergency share links expire automatically and can be revoked by the user at any moment.
6. **No Background Tracking:** GPS coordinates are requested strictly upon user action (e.g. searching from current location or activating SOS) and are never tracked passively in the background.

---

## ⚠️ Important Safety & Legal Disclaimer

SafePath AI is an educational, community-driven route discovery and peer assistance platform.

- **Estimates Only:** Route safety scores and hazard maps represent preliminary estimates based strictly on community reports and infrastructure alerts. They do not constitute an endorsement of any path as risk-free or a guarantee of personal safety.
- **Emergency Services:** In any urgent or life-threatening situation, always dial your local emergency services (e.g., **112**, **911**, or **100**) immediately. SafePath AI is not an emergency response provider.

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
