from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime

from app.db.database import get_db
from app.db import models
from app.services.qr_service import generate_order_qr
from app.services.order_worker import cancel_expired_orders

router = APIRouter(prefix='/cart', tags=['Cart'])
templates = Jinja2Templates(directory='templates')

def get_current_customer(request: Request, db: Session):
    user_id = request.cookies.get('user_id')
    if not user_id:
        return None
    return db.query(models.Customer).filter(models.Customer.user_id == int(user_id)).first()

def get_reserved_quantity(stock_id: int, db: Session) -> int:
    """Возвращает количество забронированного, но еще не выданного товара"""
    result = db.query(func.sum(models.OrderItem.quantity)).filter(
        models.OrderItem.stock_id == stock_id,
        models.OrderItem.status == 'Pending'
    ).scalar()
    return int(result or 0)

@router.get('')
def view_cart(request: Request, db: Session = Depends(get_db)):
    cancel_expired_orders(db)
    customer = get_current_customer(request, db)
    if not customer:
        return RedirectResponse(url='/account/login', status_code=303)

    cart_order = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.customer_id == customer.customer_id,
        models.CustomerOrder.status == 'cart'
    ).first()

    items = cart_order.items if cart_order else []
    total_cost = sum(item.quantity * (item.stock.price or 0) for item in items if item.stock)

    # Передаем доступный остаток для ограничения кнопок +
    items_with_avail = []
    for item in items:
        if item.stock:
            reserved = get_reserved_quantity(item.stock_id, db)
            # Доступно = Физический остаток - Забронировано другими
            available = max(0, (item.stock.quantity or 0) - reserved + item.quantity)
            items_with_avail.append({
                'item': item,
                'available': available
            })

    return templates.TemplateResponse(
        request=request, name='cart.html',
        context={'cart_order': cart_order, 'items_data': items_with_avail, 'total_cost': total_cost, 'title': 'Корзина'}
    )

@router.post('/add')
def add_to_cart(
    request: Request,
    stock_id: int = Form(...),
    quantity: int = Form(1),
    db: Session = Depends(get_db)
):
    customer = get_current_customer(request, db)
    if not customer:
        return RedirectResponse(url='/account/login', status_code=303)

    stock = db.query(models.PharmacyStock).filter(models.PharmacyStock.stock_id == stock_id).first()
    if not stock:
        return RedirectResponse(url='/catalog', status_code=303)

    reserved = get_reserved_quantity(stock_id, db)
    available = max(0, (stock.quantity or 0) - reserved)

    if available < quantity:
        return RedirectResponse(url='/catalog', status_code=303)

    cart_order = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.customer_id == customer.customer_id,
        models.CustomerOrder.status == 'cart'
    ).first()

    if not cart_order:
        cart_order = models.CustomerOrder(customer_id=customer.customer_id, status='cart', total_cost=0)
        db.add(cart_order)
        db.commit()
        db.refresh(cart_order)

    existing_item = db.query(models.OrderItem).filter(
        models.OrderItem.order_id == cart_order.order_id,
        models.OrderItem.stock_id == stock_id
    ).first()

    if existing_item:
        if available >= quantity:
            existing_item.quantity += quantity
    else:
        new_item = models.OrderItem(order_id=cart_order.order_id, stock_id=stock_id, quantity=quantity, status='Pending')
        db.add(new_item)

    db.commit()
    return RedirectResponse(url='/cart', status_code=303)

@router.post('/update')
def update_cart_item(
    request: Request,
    order_item_id: int = Form(...),
    action: str = Form(...),
    db: Session = Depends(get_db)
):
    customer = get_current_customer(request, db)
    if not customer:
        return RedirectResponse(url='/account/login', status_code=303)

    item = db.query(models.OrderItem).filter(models.OrderItem.order_item_id == order_item_id).first()
    if item and item.order.customer_id == customer.customer_id and item.order.status == 'cart':
        if action == 'increase':
            reserved = get_reserved_quantity(item.stock_id, db)
            available = max(0, (item.stock.quantity or 0) - reserved)
            if available > 0:
                item.quantity += 1
        elif action == 'decrease':
            if item.quantity > 1:
                item.quantity -= 1
            else:
                db.delete(item)
        elif action == 'remove':
            db.delete(item)
        db.commit()

    return RedirectResponse(url='/cart', status_code=303)

@router.post('/checkout')
def checkout(request: Request, db: Session = Depends(get_db)):
    customer = get_current_customer(request, db)
    if not customer:
        return RedirectResponse(url='/account/login', status_code=303)

    cart_order = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.customer_id == customer.customer_id,
        models.CustomerOrder.status == 'cart'
    ).first()

    if not cart_order or not cart_order.items:
        return RedirectResponse(url='/cart', status_code=303)

    # Проверяем наличие перед перевод в активный заказ (ФИЗИЧЕСКИЙ ОСТАТОК НЕ УМЕНЬШАЕМ!)
    for item in cart_order.items:
        reserved = get_reserved_quantity(item.stock_id, db)
        available = max(0, (item.stock.quantity or 0) - reserved + item.quantity)
        if item.quantity > available:
            return RedirectResponse(url='/cart', status_code=303)

    cart_order.status = 'active'
    cart_order.created_at = datetime.datetime.utcnow()
    cart_order.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    cart_order.total_cost = sum(item.quantity * (item.stock.price or 0) for item in cart_order.items if item.stock)

    generate_order_qr(cart_order.order_id)
    db.commit()

    return RedirectResponse(url='/profile', status_code=303)
