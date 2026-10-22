from fastapi import APIRouter, Depends, Request, Query
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.db.database import get_db
from app.db import models

router = APIRouter(tags=['Catalog'])
templates = Jinja2Templates(directory='templates')

def get_reserved_quantity(stock_id: int, db: Session) -> int:
    result = db.query(func.sum(models.OrderItem.quantity)).filter(
        models.OrderItem.stock_id == stock_id,
        models.OrderItem.status == 'Pending'
    ).scalar()
    return int(result or 0)

@router.get('/')
def home_page(request: Request, db: Session = Depends(get_db)):
    popular_products = (
        db.query(models.Product)
        .join(models.PharmacyStock, models.Product.product_id == models.PharmacyStock.product_id)
        .join(models.OrderItem, models.PharmacyStock.stock_id == models.OrderItem.stock_id)
        .group_by(models.Product.product_id)
        .order_by(func.sum(models.OrderItem.quantity).desc())
        .limit(6)
        .all()
    )

    if len(popular_products) < 6:
        existing_ids = [p.product_id for p in popular_products]
        additional_products = (
            db.query(models.Product)
            .filter(models.Product.product_id.not_in(existing_ids) if existing_ids else True)
            .limit(6 - len(popular_products))
            .all()
        )
        popular_products.extend(additional_products)

    pharmacies_count = db.query(models.Pharmacy).count()
    products_count = db.query(models.Product).count()

    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'popular_products': popular_products,
            'pharmacies_count': pharmacies_count,
            'products_count': products_count,
            'title': 'Главная — Поиск лекарств в аптеках'
        }
    )

@router.get('/api/search_suggest')
def search_suggest(q: Optional[str] = Query(None), db: Session = Depends(get_db)):
    if not q or len(q.strip()) < 1:
        return []

    products = db.query(models.Product).filter(
        (models.Product.name.ilike(f'%{q.strip()}%')) |
        (models.Product.active_substance.ilike(f'%{q.strip()}%'))
    ).limit(6).all()

    return [
        {
            "product_id": p.product_id,
            "name": p.name,
            "form": p.form or "",
            "dosage": p.dosage or "",
            "image": p.display_image
        }
        for p in products
    ]

@router.get('/catalog')
def catalog_page(
    request: Request,
    q: Optional[str] = Query(None),
    form: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(models.Product)
    if q:
        query = query.filter(
            (models.Product.name.ilike(f'%{q}%')) |
            (models.Product.active_substance.ilike(f'%{q}%'))
        )
    if form and form != 'all':
        query = query.filter(models.Product.form == form)

    products = query.order_by(models.Product.name).all()
    forms = [f[0] for f in db.query(models.Product.form).distinct().all() if f[0]]

    return templates.TemplateResponse(
        request=request, name='catalog.html',
        context={'products': products, 'forms': forms, 'q': q or '', 'selected_form': form or 'all', 'title': 'Каталог лекарств'}
    )

@router.get('/product/{product_id}')
def product_card(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.product_id == product_id).first()
    if not product:
        return templates.TemplateResponse(request=request, name='404.html', context={'title': 'Товар не найден'}, status_code=404)

    raw_stocks = db.query(models.PharmacyStock).filter(models.PharmacyStock.product_id == product_id).all()

    stocks_data = []
    for s in raw_stocks:
        reserved = get_reserved_quantity(s.stock_id, db)
        available = max(0, (s.quantity or 0) - reserved)

        if available > 0:
            stocks_data.append({
                'stock': s,
                'available': available
            })

    user_id = request.cookies.get('user_id')
    user_lat = 53.9045
    user_lon = 27.5615
    user_address = "г. Минск (по умолчанию)"
    has_db_coords = False

    if user_id and str(user_id).isdigit():
        customer = db.query(models.Customer).filter(models.Customer.user_id == int(user_id)).first()
        if customer and customer.latitude is not None and customer.longitude is not None:
            user_lat = float(customer.latitude)
            user_lon = float(customer.longitude)
            user_address = customer.default_address or "Адрес из вашего профиля"
            has_db_coords = True

    return templates.TemplateResponse(
        request=request, name='product_card.html',
        context={
            'product': product,
            'stocks_data': stocks_data,
            'user_lat': user_lat,
            'user_lon': user_lon,
            'user_address': user_address,
            'has_db_coords': has_db_coords,
            'title': product.name
        }
    )
