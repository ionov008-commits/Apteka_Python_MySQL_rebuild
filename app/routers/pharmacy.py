from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.database import get_db
from app.db import models

router = APIRouter(prefix='/pharmacy', tags=['Pharmacy'])
templates = Jinja2Templates(directory='templates')

@router.get('/manager')
def manager_dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get('user_id')
    if not user_id:
        return RedirectResponse(url='/account/login', status_code=303)

    pharmacy = db.query(models.Pharmacy).filter(models.Pharmacy.user_id == int(user_id)).first()
    if not pharmacy:
        return RedirectResponse(url='/catalog', status_code=303)

    stocks = db.query(models.PharmacyStock).filter(models.PharmacyStock.pharmacy_id == pharmacy.pharmacy_id).all()

    reservations = db.query(models.OrderItem).filter(
        models.OrderItem.stock.has(pharmacy_id=pharmacy.pharmacy_id),
        models.OrderItem.status == 'Pending'
    ).all()

    reserved_map = {}
    for r in reservations:
        reserved_map[r.stock_id] = reserved_map.get(r.stock_id, 0) + r.quantity

    stocks_info = []
    for s in stocks:
        stocks_info.append({
            'stock': s,
            'reserved': reserved_map.get(s.stock_id, 0)
        })

    existing_product_ids = [s.product_id for s in stocks]
    available_products = db.query(models.Product).filter(~models.Product.product_id.in_(existing_product_ids)).all() if existing_product_ids else db.query(models.Product).all()

    total_items = sum(s.quantity or 0 for s in stocks)
    total_value = sum((s.quantity or 0) * (s.price or 0) for s in stocks)

    return templates.TemplateResponse(
        request=request, name='pharmacy/manager.html',
        context={
            'pharmacy': pharmacy,
            'stocks_info': stocks_info,
            'available_products': available_products,
            'total_items': total_items,
            'total_value': total_value,
            'title': 'Панель руководителя'
        }
    )

@router.post('/manager/stock/update')
def update_stock(stock_id: int = Form(...), quantity: int = Form(...), price: float = Form(...), db: Session = Depends(get_db)):
    stock = db.query(models.PharmacyStock).filter(models.PharmacyStock.stock_id == stock_id).first()
    if stock:
        stock.quantity = quantity
        stock.price = price
        db.commit()
    return RedirectResponse(url='/pharmacy/manager', status_code=303)

@router.post('/manager/stock/add')
def add_stock(product_id: int = Form(...), quantity: int = Form(...), price: float = Form(...), request: Request = None, db: Session = Depends(get_db)):
    user_id = request.cookies.get('user_id')
    pharmacy = db.query(models.Pharmacy).filter(models.Pharmacy.user_id == int(user_id)).first()
    if pharmacy:
        new_stock = models.PharmacyStock(pharmacy_id=pharmacy.pharmacy_id, product_id=product_id, quantity=quantity, price=price)
        db.add(new_stock)
        db.commit()
    return RedirectResponse(url='/pharmacy/manager', status_code=303)

@router.get('/pharmacist')
def pharmacist_dashboard(request: Request, order_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    user_id = request.cookies.get('user_id')
    if not user_id:
        return RedirectResponse(url='/account/login', status_code=303)

    pharmacist = db.query(models.Pharmacist).filter(models.Pharmacist.user_id == int(user_id)).first()
    if not pharmacist:
        pharmacist = db.query(models.Pharmacist).first()
        if not pharmacist:
            return RedirectResponse(url='/catalog', status_code=303)

    target_order = None
    order_items = []

    if order_id:
        target_order = db.query(models.CustomerOrder).filter(models.CustomerOrder.order_id == order_id).first()
        if target_order:
            order_items = db.query(models.OrderItem).filter(
                models.OrderItem.order_id == order_id,
                models.OrderItem.stock.has(pharmacy_id=pharmacist.pharmacy_id)
            ).all()

    return templates.TemplateResponse(
        request=request, name='pharmacy/pharmacist.html',
        context={
            'pharmacist': pharmacist,
            'order': target_order,
            'order_items': order_items,
            'search_id': order_id or '',
            'title': 'Рабочее место фармацевта'
        }
    )

@router.post('/pharmacist/dispense')
def dispense_order(
    order_id: int = Form(...),
    cancelled_item_ids: List[int] = Form([]),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user_id = request.cookies.get('user_id')
    pharmacist = db.query(models.Pharmacist).filter(models.Pharmacist.user_id == int(user_id)).first() if user_id else db.query(models.Pharmacist).first()

    order = db.query(models.CustomerOrder).filter(models.CustomerOrder.order_id == order_id).first()
    if order and pharmacist:
        order_items = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order_id,
            models.OrderItem.stock.has(pharmacy_id=pharmacist.pharmacy_id)
        ).all()

        for item in order_items:
            if item.order_item_id in cancelled_item_ids:
                item.status = 'Cancelled'
            else:
                item.status = 'Dispensed'
                if item.stock:
                    item.stock.quantity = max(0, (item.stock.quantity or 0) - item.quantity)

        db.commit()

        pending_left = db.query(models.OrderItem).filter(
            models.OrderItem.order_id == order_id,
            models.OrderItem.status == 'Pending'
        ).count()

        if pending_left == 0:
            order.status = 'выдан'
            db.commit()

    return RedirectResponse(url=f'/pharmacy/pharmacist?order_id={order_id}', status_code=303)
