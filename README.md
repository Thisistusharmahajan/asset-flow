# AssetFlow

AssetFlow is a full-stack Asset Management System that helps organizations efficiently manage company assets, employee allocations, maintenance requests, resource bookings, transfer requests, and notifications from a centralized dashboard.

The application provides secure authentication, real-time dashboard statistics, and a modern user interface for tracking organizational assets.

# Problem Statement

Organizations often struggle to maintain records of company assets due to manual processes or disconnected systems. This leads to:

- Difficulty tracking asset allocation
- Delayed maintenance requests
- Poor visibility of available assets
- Inefficient transfer management
- Lack of centralized dashboard and reports

AssetFlow solves these challenges by providing a centralized asset management platform where administrators and employees can manage assets efficiently.



# Tech Stack

## Frontend

- React 19
- HTML5
- CSS3
- JavaScript (ES6+)


## Backend

- Python


# Database

Development Database

- PostgreSQL




# Backend Dependencies

```
Flask
Flask-SQLAlchemy
Flask-JWT-Extended
Flask-CORS
python-dotenv
```

---

# Frontend Dependencies

```
React
React DOM
React Router DOM
Vite
```

---

# Installation Guide

## 1. Clone Repository

```bash
git clone <repository-url>

cd asset-flow
```

---

# Backend Setup

### Navigate to Backend

```bash
cd backend
```

### Create Virtual Environment (Optional)

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux / Mac

```bash
python3 -m venv venv

source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Create Demo Database

```bash
python seed.py
```

### Run Backend Server

```bash
python app.py
```

Backend runs at:

```
http://localhost:5000
```

---

# Frontend Setup

Open another terminal.

Navigate to frontend

```bash
cd frontend
```

Install packages

```bash
npm install
```

Start development server

```bash
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

# Environment Variables

For PostgreSQL

```
DATABASE_URL=postgresql://username:password@localhost:5432/assetflow
```

# Team Member

Tushar Mahajan, Arushi Nirala, Kedareswari Bandaru
