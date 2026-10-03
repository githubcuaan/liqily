import os

from fastapi import FastAPI, Response
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI(title="liqi-data")
engine = create_engine(os.environ["WORKER_DATABASE_URL"], pool_pre_ping=True)


@app.get("/health")
def health(response: Response):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "db": "up"}
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "error", "db": "down"}
