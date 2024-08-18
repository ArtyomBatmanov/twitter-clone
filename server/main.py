from fastapi import FastAPI, Depends, HTTPException, Header
from .schemas import Tweet, TweetCreate, TweetResponse
from .database import get_db
from sqlalchemy.orm import Session
from .crud import add_tweet
from .utils import get_api_key, get_user_by_api_key
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from .models import User

app = FastAPI()

app.mount("/static", StaticFiles(directory="../client/static"), name="static")
app.mount("/js", StaticFiles(directory="../client/static/js"), name="js")
app.mount("/css", StaticFiles(directory="../client/static/css"), name="css")


def get_current_user(api_key: str = Header(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.api_key == api_key).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user


@app.get("/index")
def read_main():
    return FileResponse("../client/static/index.html")


@app.post("/api/tweets", response_model=TweetResponse)
def create_tweet(
        tweet: TweetCreate,  # Убедитесь, что здесь используется TweetCreate
        api_key: str = Header(..., alias="api-key"),
        db: Session = Depends(get_db)
):
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_tweet = add_tweet(db=db, tweet=tweet, user_id=user.id)
    return db_tweet