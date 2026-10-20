import datetime
from sqlalchemy.orm import Session
from app.db import models


def cancel_expired_orders(db: Session):
    """Снимает просроченные брони и возвращает товары на склад"""
    now = datetime.datetime.utcnow()

    expired_orders = db.query(models.CustomerOrder).filter(
        models.CustomerOrder.status.in_(["active", "booked", "новый"]),
        models.CustomerOrder.expires_at.isnot(None),
        models.CustomerOrder.expires_at < now
    ).all()

    for order in expired_orders:
        order.status = "cancelled"
        for item in order.items:
            item.status = "Cancelled"
            if item.stock:
                item.stock.quantity += item.quantity

    if expired_orders:
        db.commit()