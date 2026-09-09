from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import Base, engine, migrate
from .seed import seed
from .routers import auth as auth_r, cases as cases_r, analyze as analyze_r, report as report_r
from .routers import audit as audit_r, alerts as alerts_r, params as params_r
from .routers import stats as stats_r, entities as entities_r
from .ratelimit import RateLimitMiddleware

Base.metadata.create_all(bind=engine)
migrate()
seed()

app = FastAPI(title="SIH26183 — Blockchain Cybercrime Investigation API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware, per_minute=settings.RATE_LIMIT_PER_MINUTE,
                    login_per_minute=settings.RATE_LIMIT_LOGIN_PER_MINUTE)

app.include_router(auth_r.router)
app.include_router(cases_r.router)
app.include_router(analyze_r.router)
app.include_router(report_r.router)
app.include_router(audit_r.router)
app.include_router(alerts_r.router)
app.include_router(params_r.router)
app.include_router(stats_r.router)
app.include_router(entities_r.router)


@app.get("/")
def root():
    return {"service": "SIH26183 investigation API", "docs": "/docs",
            "demo_login": {"username": "investigator", "password": "cyber123"},
            "endpoints": ["POST /api/auth/login", "POST /api/analyze", "GET /api/cases",
                          "GET /api/alerts", "GET /api/audit", "GET /api/config/weights",
                          "GET /api/report/{case_id}", "GET /docs"]}


@app.get("/api/health")
def health():
    return {"ok": True}
