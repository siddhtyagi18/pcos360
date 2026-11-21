# PCOS360 — Local Setup & Development Guide

## 1. Prerequisites

- **Python**: 3.11 or 3.12 (with pip)
- **Node.js**: v18+ or v20+ (with npm)
- **Java Development Kit**: JDK 17 (for Android mobile build)
- **Android SDK**: Build tools 37.0.0, API 34+
- **Database**: PostgreSQL 15+ (local or Supabase cloud instance)
- **API Keys**: Google Gemini API key (optional: Groq API key)

---

## 2. Repository Cloning

```bash
git clone https://github.com/your-org/pcos360.git
cd pcos360
```

---

## 3. Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables (`backend/.env`):
   ```env
   PROJECT_NAME="PCOS360 API"
   ENVIRONMENT=development
   DEBUG=True
   SECRET_KEY=at_least_32_characters_random_string_here
   DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/pcos360_db
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-flash-lite-latest
   GROQ_API_KEY=
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

5. Start the backend server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Open `http://localhost:8000/docs` in your browser to verify Swagger UI.

---

## 4. Frontend Setup (React 19 + Vite)

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables (`frontend/.env`):
   ```env
   VITE_API_URL=http://localhost:8000/api
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` to view the web application.

---

## 5. Mobile App Setup (React Native + Expo)

1. Open a new terminal and navigate to the mobile directory:
   ```bash
   cd mobile
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables (`mobile/.env`):
   ```env
   EXPO_PUBLIC_API_URL=https://pcos360-backend.onrender.com/api
   ```

4. Start the Expo Metro bundler:
   ```bash
   npx expo start
   ```

5. Build or run on Android:
   ```bash
   cd android
   ./gradlew assembleRelease
   ```

