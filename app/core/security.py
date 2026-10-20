import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля с хэшем $2a$ из MySQL через чистый bcrypt"""
    try:
        # bcrypt принимает максимум 72 байта
        password_bytes = plain_password.encode('utf-8')[:72]
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """Хэширование нового пароля при регистрации"""
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')