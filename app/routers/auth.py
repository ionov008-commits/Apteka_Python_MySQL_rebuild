from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.db import models
from app.core.security import verify_password, get_password_hash

router = APIRouter(prefix='/account', tags=['Auth'])
templates = Jinja2Templates(directory='templates')

@router.get('/login')
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name='account/login.html', context={'title': 'Вход в систему'})

@router.post('/login')
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        (models.User.Username == username) | (models.User.Email == username)
    ).first()

    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse(
            request=request, name='account/login.html',
            context={'error': 'Неверный логин или пароль', 'title': 'Вход в систему'},
            status_code=400
        )

    target_url = '/catalog'
    if user.role == 'owner':
        target_url = '/pharmacy/manager'
    elif user.role == 'pharmacist':
        target_url = '/pharmacy/pharmacist'
    elif user.role == 'admin':
        target_url = '/admin/dashboard'

    res = RedirectResponse(url=target_url, status_code=303)
    res.set_cookie(key='user_id', value=str(user.user_id), httponly=True)
    res.set_cookie(key='user_role', value=str(user.role), httponly=True)
    return res

@router.get('/logout')
def logout():
    res = RedirectResponse(url='/', status_code=303)
    res.delete_cookie('user_id')
    res.delete_cookie('user_role')
    return res

@router.get('/register')
def register_page(request: Request, db: Session = Depends(get_db)):
    pharmacies = db.query(models.Pharmacy).all()
    return templates.TemplateResponse(
        request=request, name='account/register.html',
        context={'pharmacies': pharmacies, 'title': 'Регистрация'}
    )

@router.post('/register')
def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    address: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    pharmacy_id: Optional[int] = Form(None),
    pharmacy_name: Optional[str] = Form(None),
    pharmacy_address: Optional[str] = Form(None),
    pharmacy_phone: Optional[str] = Form(None),
    pharmacy_working_hours: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    pharmacies = db.query(models.Pharmacy).all()

    existing = db.query(models.User).filter((models.User.Username == username) | (models.User.Email == email)).first()
    if existing:
        return templates.TemplateResponse(
            request=request, name='account/register.html',
            context={'error': 'Пользователь с таким логином или Email уже существует', 'pharmacies': pharmacies, 'title': 'Регистрация'},
            status_code=400
        )

    if role == 'pharmacist' and not pharmacy_id:
        return templates.TemplateResponse(
            request=request, name='account/register.html',
            context={'error': 'Выберите аптеку для работы фармацевта', 'pharmacies': pharmacies, 'title': 'Регистрация'},
            status_code=400
        )

    if role == 'owner' and not pharmacy_name:
        return templates.TemplateResponse(
            request=request, name='account/register.html',
            context={'error': 'Укажите название и данные регистрируемой аптеки', 'pharmacies': pharmacies, 'title': 'Регистрация'},
            status_code=400
        )

    new_user = models.User(
        Username=username,
        Email=email,
        password=get_password_hash(password),
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if role == 'customer':
        customer = models.Customer(
            user_id=new_user.user_id,
            full_name=full_name,
            phone=phone,
            default_address=address,
            latitude=latitude,
            longitude=longitude
        )
        db.add(customer)

    elif role == 'pharmacist' and pharmacy_id:
        pharmacist = models.Pharmacist(
            user_id=new_user.user_id,
            pharmacy_id=pharmacy_id,
            full_name=full_name,
            working_hours='Пн-Пт: 09:00-18:00'
        )
        db.add(pharmacist)

    elif role == 'owner':
        pharmacy = models.Pharmacy(
            user_id=new_user.user_id,
            name=pharmacy_name,
            address=pharmacy_address or address or "Адрес не указан",
            phone=pharmacy_phone or phone,
            director_name=full_name,
            working_hours=pharmacy_working_hours or "08:00-22:00 ежедневно",
            latitude=latitude,
            longitude=longitude
        )
        db.add(pharmacy)

    db.commit()
    return templates.TemplateResponse(
        request=request, name='account/register_success.html',
        context={'title': 'Регистрация завершена'}
    )
