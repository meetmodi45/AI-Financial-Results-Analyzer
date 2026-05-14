# AI Financial Results Analyzer

An end-to-end, fully autonomous, non-LLM based AI platform to ingest, parse, classify, and analyze company financial results (PDFs) and provide retail-investor friendly summaries and verdict predictions.

## Architecture
- **Frontend**: React (Vite) + TailwindCSS + Recharts
- **Backend API**: FastAPI (Python)
- **Task Queue**: Celery
- **Message Broker**: Redis
- **Database**: PostgreSQL
- **Machine Learning**: Scikit-Learn, XGBoost, PyMuPDF, layoutparser

## Running Locally (Docker Compose)

The easiest way to run the entire backend stack locally is to use Docker Compose.

1. Create a `.env` file in the root directory (an example is provided).
2. Start the database and message broker:
   ```bash
   docker-compose up -d
   ```
3. Install backend dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Run the Celery Worker (in a separate terminal):
   ```bash
   cd backend
   celery -A app.core.celery_app worker --loglevel=info -Q main-queue
   ```
6. Start the Frontend (in a separate terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Deployment Guide (Production)

To deploy this architecture to the public internet so anyone can use it, we will use **Vercel** for the Frontend and **Render** for the Backend infrastructure.

### 1. Deploying the Database & Redis (Render)
1. Go to [Render.com](https://render.com) and create a New **PostgreSQL** instance. Note the internal and external connection URLs.
2. Create a New **Redis** instance. Note the internal connection URL.

### 2. Deploying the Backend APIs & Celery Workers (Render)
1. Create a New **Web Service** on Render and connect your GitHub repository.
2. Set the Root Directory to `backend`.
3. Set the Build Command to `pip install -r requirements.txt`.
4. Set the Start Command to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Under Environment Variables, add your `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `REDIS_URL` pointing to the instances created in step 1.
6. **Deploy the Celery Worker**: Create a New **Background Worker** on Render. Point it to the same repository and root directory (`backend`). Set the start command to:
   `celery -A app.core.celery_app worker --loglevel=info -Q main-queue`
   Ensure the worker shares the exact same Environment Variables so it can connect to the DB and Redis.

### 3. Deploying the Frontend (Vercel)
1. Go to [Vercel.com](https://vercel.com) and import your GitHub repository.
2. Set the Root Directory to `frontend`.
3. Vercel will automatically detect Vite. 
4. **Crucial Step:** In `frontend/src/App.jsx`, update the `API_BASE` variable from `http://localhost:8000/api/v1` to your new live Render API URL (e.g. `https://your-api.onrender.com/api/v1`). 
*(Alternatively, you can extract this into a `.env.production` file for Vite to use automatically `import.meta.env.VITE_API_BASE`).*
5. Click **Deploy**.

## ML Model Training
If you ever need to retrain the offline ML agents (Document Classifier or Verdict Classifier), run the scripts located in `backend/training/` and restart the Celery worker to load the new weights into memory.
