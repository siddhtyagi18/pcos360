import time
import statistics
import concurrent.futures
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.user import User

client = TestClient(app)

def benchmark_db():
    print("\n--- DATABASE PERFORMANCE BENCHMARK ---")
    latencies = []
    with SessionLocal() as db:
        for _ in range(10):
            t0 = time.perf_counter()
            db.execute(text("SELECT 1")).scalar()
            latencies.append((time.perf_counter() - t0) * 1000)
    
    avg_lat = statistics.mean(latencies)
    p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
    print(f"PostgreSQL Ping (SELECT 1) over 10 runs:")
    print(f"  Average: {avg_lat:.2f} ms | Min: {min(latencies):.2f} ms | Max: {max(latencies):.2f} ms")
    assert avg_lat < 300, f"DB latency too high: {avg_lat} ms"
    return avg_lat

def benchmark_endpoints():
    print("\n--- FASTAPI ENDPOINT LATENCY BENCHMARK ---")
    
    # 1. Health endpoint (no auth)
    health_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        resp = client.get("/api/health")
        assert resp.status_code == 200
        health_times.append((time.perf_counter() - t0) * 1000)
    print(f"GET /api/health over 10 runs:")
    print(f"  Average: {statistics.mean(health_times):.2f} ms | Min: {min(health_times):.2f} ms | Max: {max(health_times):.2f} ms")
    
    # 2. Context Builder & PCOSCOPE for existing test/admin user (if exists) or new temp user
    # Find any user in DB to test context retrieval
    with SessionLocal() as db:
        user = db.query(User).filter(User.is_active == True, User.is_demo == False).first()
        if user:
            import secrets
            from app.models.user_session import UserSession
            from datetime import timedelta, timezone, datetime
            jti = secrets.token_urlsafe(32)
            token, expires_at = create_access_token(user_id=user.id, jti=jti)
            session = UserSession(
                user_id=user.id,
                token_jti=jti,
                user_agent="PerformanceTest/1.0",
                expires_at=expires_at,
            )
            db.add(session)
            db.commit()
            
            headers = {"Authorization": f"Bearer {token}"}
            
            pcoscope_times = []
            for _ in range(5):
                t0 = time.perf_counter()
                resp = client.get("/api/pcoscope/analysis", headers=headers)
                assert resp.status_code == 200
                pcoscope_times.append((time.perf_counter() - t0) * 1000)
            print(f"GET /api/pcoscope/analysis over 5 runs (with DB fetch & deterministic computation):")
            print(f"  Average: {statistics.mean(pcoscope_times):.2f} ms | Min: {min(pcoscope_times):.2f} ms | Max: {max(pcoscope_times):.2f} ms")
            
            context_times = []
            for _ in range(5):
                t0 = time.perf_counter()
                resp = client.get("/api/health-context/me", headers=headers)
                assert resp.status_code == 200
                context_times.append((time.perf_counter() - t0) * 1000)
            print(f"GET /api/health-context/me over 5 runs:")
            print(f"  Average: {statistics.mean(context_times):.2f} ms | Min: {min(context_times):.2f} ms | Max: {max(context_times):.2f} ms")

            # Clean up the test session
            db.delete(session)
            db.commit()

def benchmark_concurrency():
    print("\n--- CONCURRENCY TEST (10 CONCURRENT REQUESTS) ---")
    def fetch_health():
        t0 = time.perf_counter()
        resp = client.get("/api/health")
        return resp.status_code, (time.perf_counter() - t0) * 1000
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_health) for _ in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    statuses = [r[0] for r in results]
    latencies = [r[1] for r in results]
    print(f"10 Concurrent GET /api/health requests:")
    print(f"  All HTTP 200: {all(s == 200 for s in statuses)}")
    print(f"  Average: {statistics.mean(latencies):.2f} ms | Max: {max(latencies):.2f} ms")

if __name__ == "__main__":
    benchmark_db()
    benchmark_endpoints()
    benchmark_concurrency()
    print("\n✓ Performance benchmarks completed successfully.")
