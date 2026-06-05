

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from app.routers import admin, auth, cargo, logistics, orders, payments, users
from app.core.config import settings
from app.core.database import init_db
from app.middleware.security import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при старте приложения."""
    await init_db()
    yield


app = FastAPI(
    title="Groozer API",
    description="API для веб-приложения организации грузоперевозок",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)


app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)


app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/assets", StaticFiles(directory="templates"), name="assets")

templates = Jinja2Templates(directory="templates")


app.include_router(auth.router,   prefix="/api/auth",   tags=["Аутентификация"])
app.include_router(users.router,  prefix="/api/users",  tags=["Пользователи"])
app.include_router(orders.router, prefix="/api/orders", tags=["Заявки"])
app.include_router(cargo.router,  prefix="/api/cargo",  tags=["Грузы"])
app.include_router(logistics.router, prefix="/api/logistics", tags=["Логистика"])
app.include_router(payments.router, prefix="/api/payments", tags=["Платежи"])
app.include_router(admin.router, prefix="/api/admin", tags=["Администрирование"])


from fastapi.responses import FileResponse
import os

PARTIALS_DIR = os.path.join(os.path.dirname(__file__), "partials")

@app.get("/partial/{page}", include_in_schema=False)
async def serve_partial(page: str):
    """Возвращает только <style>+<main> для SPA-роутера (без оболочки)."""
    safe = page.replace("..", "").replace("/", "")
    path = os.path.join(PARTIALS_DIR, f"{safe}.html")
    if not os.path.exists(path):
        path = os.path.join(PARTIALS_DIR, "home.html")
    return FileResponse(path, media_type="text/html")


@app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
async def serve_shell(request: Request, full_path: str):
    """Всегда отдаёт shell.html — роутер на клиенте сам загрузит нужный партиал."""
    return templates.TemplateResponse("shell.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
        log_level="info",
        access_log=True,
    )
