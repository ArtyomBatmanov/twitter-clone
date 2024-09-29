from fastapi import Header, HTTPException
from models import User
from sqlalchemy.orm import Session


def get_api_key(api_key: str = Header(None)) -> str:
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key missing")
    return api_key


def get_user_by_api_key(db: Session, api_key: str) -> User:
    """
    Ищет пользователя в базе данных по его API-ключу.

    :param db: Сессия базы данных
    :param api_key: API-ключ пользователя
    :return: Объект пользователя или None, если пользователь не найден
    """
    return db.query(User).filter(User.api_key == api_key).first()
