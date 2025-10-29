from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers.api import router

app = FastAPI(
    title="Taipei Hackathon Microservice",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/docs/openapi.json",
)

origins = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://localhost:3000",
    "http://localhost:8080",
    "https://townpass-microservice.web.app",
    "https://townpass-microservice.firebaseapp.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["API"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Taipei Hackathon Microservice!"}

@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # 可改為紀錄日誌，不要讓整個服務啟動失敗
        print(f"[startup] DB init skipped: {e}")