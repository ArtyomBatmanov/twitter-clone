from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models import User

DATABASE_URL = "postgresql://admin:admin@localhost/twitter_clone"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_user(db, name: str, api_key: str):
    new_user = User(name=name, api_key=api_key)
    db.add(new_user)
    try:
        db.commit()
        print(f"User '{name}' created successfully.")
    except IntegrityError:
        db.rollback()
        print(f"Error: User with name '{name}' or API key '{api_key}' already exists.")


if __name__ == "__main__":
    db = SessionLocal()
    user_name = "example_user"
    user_api_key = "test"
    create_user(db, user_name, user_api_key)
    db.close()
