import math
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.database import get_db
from app.db import models
from app.services.order_worker import cancel_expired_orders

router = APIRouter(tags=["Catalog"])
templates = Jinja2Templates(directory="templates")


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


@router.get("/catalog")
def catalog_page(
    request: Request,
    q: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    cancel_expired_orders(db)
    query = db.query(models.Product)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            or_(
                models.Product.name.ilike(search_pattern),
                models.Product.active_substance.ilike(search_pattern),
                models.Product.description.ilike(search_pattern)
            )
        )

    if form:
        query = query.filter(models.Product.form == form)

    products = query.all()
    forms = [f[0] for f in db.query(models.Product.form).distinct().all() if f[0]]

    return templates.TemplateResponse(
        request=request,
        name="catalog.html",
        context={
            "products": products,
            "search_query": q or "",
            "selected_form": form or "",
            "forms": forms,
            "title": "Каталог лекарств"
        }
    )


@router.get("/product/{product_id}")
def product_card(
    request: Request,
    product_id: int,
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    cancel_expired_orders(db)
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"message": "Товар не найден"},
            status_code=404
        )

    stocks = db.query(models.PharmacyStock).filter(
        models.PharmacyStock.product_id == product_id,
        models.PharmacyStock.quantity > 0
    ).all()

    pharmacies_info = []
    for stock in stocks:
        pharmacy = stock.pharmacy
        distance = None
        if user_lat is not None and user_lon is not None and pharmacy.latitude and pharmacy.longitude:
            distance = haversine(user_lat, user_lon, pharmacy.latitude, pharmacy.longitude)

        pharmacies_info.append({
            "stock_id": stock.stock_id,
            "pharmacy": pharmacy,
            "price": stock.price,
            "quantity": stock.quantity,
            "distance": distance
        })

    if user_lat is not None and user_lon is not None:
        pharmacies_info.sort(key=lambda x: (x["distance"] if x["distance"] is not None else float("inf")))

    return templates.TemplateResponse(
        request=request,
        name="product_card.html",
        context={
            "product": product,
            "pharmacies_info": pharmacies_info,
            "user_lat": user_lat,
            "user_lon": user_lon,
            "title": f"{product.name} - Детали"
        }
    )