import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Агрегатор Аптек"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mysql+pymysql://root:root@127.0.0.1:3306/kursovaya3?charset=utf8mb4")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "secret")

settings = Settings()