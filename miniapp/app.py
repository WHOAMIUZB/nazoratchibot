import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import database as db
from miniapp.api import router as miniapp_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="Kitoblar — Mini App")

# API endpoints (/api/...) — birinchi ro'yxatdan o'tkaziladi, shuning uchun
# quyidagi statik fayllar bilan to'qnashmaydi
app.include_router(miniapp_router, prefix="/api")

# Statik fayllar (index.html, app.js, style.css) — ildizda (/) xizmat qiladi
app.mount("/", StaticFiles(directory=os.path.join(BASE_DIR, "static"), html=True), name="miniapp-static")


async def run_miniapp():
    import uvicorn
    from config import MINIAPP_PORT
    await db.init_db()
    config = uvicorn.Config(app, host="0.0.0.0", port=MINIAPP_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_miniapp())
