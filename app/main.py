import os, time, json
from datetime import datetime, date
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func
from app.database import Session, Transaction, init_db, db_size
from app.inference import Predictor, load_labels

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABELS = os.path.join(ROOT, "labels.json")

app = FastAPI(title="Waste AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

predictor = Predictor()
start_time = time.time()


class TxIn(BaseModel):
    class_detected: str
    confidence: float = Field(ge=0, le=1)
    image_filename: str | None = None


class ModeIn(BaseModel):
    mode: str


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    try:
        import psutil
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
    except Exception:
        cpu = ram = None
    return {"status": "ok", "uptime": round(time.time() - start_time),
            "cpu": cpu, "ram": ram, "db_size": db_size(),
            "model": predictor.version, "mode": load_labels()[0]}


@app.post("/predict")
async def predict(request: Request):
    data = await request.body()
    if not data:
        raise HTTPException(400, "empty body")
    t0 = time.perf_counter()
    cls, conf = predictor.predict_bytes(data)
    return {"class": cls, "confidence": round(conf, 4),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}


@app.post("/transactions")
def add_tx(tx: TxIn):
    s = Session()
    row = Transaction(class_detected=tx.class_detected, confidence=tx.confidence,
                      image_filename=tx.image_filename, is_synced=False)
    s.add(row); s.commit(); s.refresh(row)
    out = row.dict(); s.close()
    return out


@app.get("/transactions")
def list_tx(limit: int = 50):
    s = Session()
    rows = s.query(Transaction).order_by(Transaction.id.desc()).limit(limit).all()
    out = [r.dict() for r in rows]; s.close()
    return out


@app.get("/stats")
def stats():
    mode, profile = load_labels()
    s = Session()
    today = datetime.combine(date.today(), datetime.min.time())
    total = s.query(func.count(Transaction.id)).filter(Transaction.timestamp >= today).scalar() or 0
    by_class = dict(s.query(Transaction.class_detected, func.count(Transaction.id))
                    .filter(Transaction.timestamp >= today)
                    .group_by(Transaction.class_detected).all())
    pending = s.query(func.count(Transaction.id)).filter(Transaction.is_synced.is_(False)).scalar() or 0
    last_sync = s.query(func.max(Transaction.timestamp)).filter(Transaction.is_synced.is_(True)).scalar()
    month = today.replace(day=1)
    trend = s.query(func.strftime("%Y-%m-%d", Transaction.timestamp), func.count(Transaction.id)) \
        .filter(Transaction.timestamp >= month) \
        .group_by(func.strftime("%Y-%m-%d", Transaction.timestamp)).all()
    s.close()
    recyc = sum(v for k, v in by_class.items() if k.lower() in ("recyclable", "glass", "can", "cardboard", "paper", "plastic", "metal"))
    return {"mode": mode, "name": profile["name"], "classes": profile["classes"],
            "colors": profile.get("colors", {}), "alert": profile.get("alert", []),
            "total_today": total, "by_class": by_class,
            "recycling_rate": round(recyc / total, 3) if total else 0,
            "pending_sync": pending, "last_sync": last_sync.isoformat() if last_sync else None,
            "trend": [{"day": d, "count": c} for d, c in trend]}


@app.get("/mode")
def get_mode():
    cfg = json.load(open(LABELS, encoding="utf-8"))
    return {"mode": cfg["active"], "available": list(cfg["profiles"].keys())}


@app.put("/mode")
def set_mode(m: ModeIn):
    cfg = json.load(open(LABELS, encoding="utf-8"))
    if m.mode not in cfg["profiles"]:
        raise HTTPException(400, "unknown mode")
    cfg["active"] = m.mode
    json.dump(cfg, open(LABELS, "w", encoding="utf-8"), indent=2)
    predictor.classes = cfg["profiles"][m.mode]["classes"]
    return {"mode": m.mode}


_static = os.path.join(ROOT, "app", "static")
if os.path.isdir(_static):
    app.mount("/static", StaticFiles(directory=_static), name="static")

@app.get("/")
def index():
    return FileResponse(os.path.join(ROOT, "app", "static", "dashboard.html"))