import time
import statistics
import sys
import urllib.request
import json
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User
from app.models.user_session import UserSession
import secrets

def log(msg):
    print(msg, flush=True)

def benchmark_db():
    log("================================================================================")
    log("1. DATABASE LATENCY BENCHMARK (SUPABASE POSTGRESQL 17)")
    log("================================================================================")
    latencies = []
    with SessionLocal() as db:
        for i in range(5):
            t0 = time.perf_counter()
            db.execute(text("SELECT 1")).scalar()
            lat = (time.perf_counter() - t0) * 1000
            latencies.append(lat)
            log(f"  Run {i+1}: {lat:.2f} ms")
    
    avg_lat = statistics.mean(latencies)
    log(f"  --> Average DB Ping Latency: {avg_lat:.2f} ms | Min: {min(latencies):.2f} ms | Max: {max(latencies):.2f} ms")
    return avg_lat

def benchmark_local_api():
    log("\n================================================================================")
    log("2. LOCAL FASTAPI ENDPOINT BENCHMARK")
    log("================================================================================")
    client = TestClient(app)

    # Health endpoint
    health_times = []
    for i in range(5):
        t0 = time.perf_counter()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        lat = (time.perf_counter() - t0) * 1000
        health_times.append(lat)
    log(f"  GET /api/health (includes live DB check) over 5 runs:")
    log(f"  --> Average: {statistics.mean(health_times):.2f} ms | Min: {min(health_times):.2f} ms | Max: {max(health_times):.2f} ms")

    # Authenticated PCOSCOPE & Health Context
    with SessionLocal() as db:
        user = db.query(User).filter(User.is_active == True, User.is_demo == False).first()
        if user:
            jti = secrets.token_urlsafe(32)
            token, expires_at = create_access_token(user_id=user.id, jti=jti)
            session = UserSession(
                user_id=user.id,
                token_jti=jti,
                user_agent="BenchmarkClient/1.0",
                expires_at=expires_at,
            )
            db.add(session)
            db.commit()
            
            headers = {"Authorization": f"Bearer {token}"}
            
            pcoscope_times = []
            for _ in range(3):
                t0 = time.perf_counter()
                resp = client.get("/api/pcoscope/analysis", headers=headers)
                assert resp.status_code == 200
                pcoscope_times.append((time.perf_counter() - t0) * 1000)
            log(f"  GET /api/pcoscope/analysis over 3 runs (DB query + deterministic analytics):")
            log(f"  --> Average: {statistics.mean(pcoscope_times):.2f} ms | Min: {min(pcoscope_times):.2f} ms | Max: {max(pcoscope_times):.2f} ms")
            
            context_times = []
            for _ in range(3):
                t0 = time.perf_counter()
                resp = client.get("/api/health-context/me", headers=headers)
                assert resp.status_code == 200
                context_times.append((time.perf_counter() - t0) * 1000)
            log(f"  GET /api/health-context/me over 3 runs:")
            log(f"  --> Average: {statistics.mean(context_times):.2f} ms | Min: {min(context_times):.2f} ms | Max: {max(context_times):.2f} ms")

            db.delete(session)
            db.commit()

def benchmark_production_render():
    log("\n================================================================================")
    log("3. PRODUCTION CLOUD AUDIT (RENDER.COM BACKEND)")
    log("================================================================================")
    url = "https://pcos360-backend.onrender.com/api/health"
    log(f"  Connecting to live URL: {url} ...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PCOS360-Audit/1.0"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            dur = (time.perf_counter() - t0) * 1000
            log(f"  ✓ HTTP Status: {resp.status}")
            log(f"  ✓ Response Time: {dur:.2f} ms")
            log(f"  ✓ Response Payload: {json.dumps(data, indent=4)}")
            log(f"  ✓ Database Status reported by Render: {data.get('database', {}).get('status')}")
    except Exception as e:
        log(f"  ! Production check exception: {e}")

if __name__ == "__main__":
    benchmark_db()
    benchmark_local_api()
    benchmark_production_render()
    log("\n================================================================================")
    log("BENCHMARK & PRODUCTION AUDIT COMPLETED")
    log("================================================================================")

