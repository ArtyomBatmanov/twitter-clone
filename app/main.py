from fastapi import FastAPI, Depends, HTTPException, Header
from .schemas import Tweet, TweetCreate
from .database import get_db
from sqlalchemy.orm import Session
from .crud import create_tweet
from .utils import get_api_key
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from .models import User
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="../static"), name="static")


def get_current_user(api_key: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == api_key).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user


@app.get("/")
def read_root():
    return FileResponse("../static/index.html")


@app.post("/api/tweets", response_model=Tweet)
def create_twee(tweet: TweetCreate, db: Session = Depends(get_db), api_key: str = Depends(get_api_key)):
    user = get_current_user(api_key, db)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid API Key")
    return create_tweet(db=db, tweet=tweet, user_id=user.id)
