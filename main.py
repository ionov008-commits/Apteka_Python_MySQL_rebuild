from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.routers import catalog, auth, cart, profile, pharmacy, admin
from app.services.order_worker import cancel_expired_orders

app = FastAPI(title="Агрегатор Аптек")

# Подключение статических файлов и шаблонов
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Регистрация всех роутеров бэкенда
app.include_router(catalog.router)
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(profile.router)
app.include_router(pharmacy.router)
app.include_router(admin.router)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = await call_next(request)
    return response


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    cancel_expired_orders(db)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"title": "Главная - Агрегатор Аптек"}
    )