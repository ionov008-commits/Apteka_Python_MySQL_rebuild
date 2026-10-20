from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db import models
from app.services.order_worker import cancel_expired_orders

router = APIRouter(prefix='/profile', tags=['Profile'])
templates = Jinja2Templates(directory='templates')

@router.get('')
def profile_page(request: Request, db: Session = Depends(get_db)):
    cancel_expired_orders(db)
    user_id = request.cookies.get('user_id')
    if not user_id:
        return RedirectResponse(url='/account/login', status_code=303)

    customer = db.query(models.Customer).filter(models.Customer.user_id == int(user_id)).first()
    if not customer:
        return RedirectResponse(url='/catalog', status_code=303)

    active_orders = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.customer_id == customer.customer_id,
        models.CustomerOrder.status.in_(['active', 'booked', 'новый'])
    ).order_by(models.CustomerOrder.created_at.desc()).all()

    past_orders = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.customer_id == customer.customer_id,
        models.CustomerOrder.status.in_(['выдан', 'cancelled'])
    ).order_by(models.CustomerOrder.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request, name='profile.html',
        context={
            'customer': customer,
            'active_orders': active_orders,
            'past_orders': past_orders,
            'title': 'Личный кабинет'
        }
    )
