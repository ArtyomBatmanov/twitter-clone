from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from .schemas import TweetCreate, TweetResponse, MediaUploadResponse
from .database import get_db
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from .crud import add_tweet, get_tweet, add_like
from .utils import get_api_key, get_user_by_api_key
from starlette.responses import FileResponse
from .models import User, Media, Follow, Like, Tweet
import shutil
import os

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
        tweet: TweetCreate,
        api_key: str = Header(..., alias="api-key"),
        db: Session = Depends(get_db)
):
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_tweet = add_tweet(db=db, tweet=tweet, user_id=user.id)
    return db_tweet


@app.post("/api/medias", response_model=MediaUploadResponse)
def upload_media(
        api_key: str = Header(..., alias="api-key"),
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    user = get_user_by_api_key(db, api_key)

    # Убедитесь, что директория для загрузок существует
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    # Создание уникального пути для сохранения файла
    file_path = os.path.join(upload_dir, file.filename)

    # Сохранение файла на диск
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Сохранение информации о файле в базе данных
    media = Media(file_path=file_path)
    db.add(media)
    db.commit()
    db.refresh(media)

    return MediaUploadResponse(result=True, media_id=media.id)


@app.delete("/api/tweets/{id}")
def delete_tweet(id: int, api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)):
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweet = get_tweet(db, id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    if tweet.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this tweet")

    db.delete(tweet)
    db.commit()

    return {"result": True}


@app.post("/api/tweets/{id}/likes")
def like_tweet(id: int, api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)):
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweet = get_tweet(db, id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    add_like(db=db, user_id=user.id, tweet_id=tweet.id)

    return {"result": True}


@app.post("/api/users/{id}/follow")
def follow_user(
        id: int,
        api_key: str = Header(..., alias="api-key"),
        db: Session = Depends(get_db)
):
    # Найти пользователя, который хочет подписаться
    follower = get_user_by_api_key(db, api_key)
    if not follower:
        raise HTTPException(status_code=404, detail="User not found")

    # Найти пользователя, на которого хотят подписаться
    followed = db.query(User).filter(User.id == id).first()
    if not followed:
        raise HTTPException(status_code=404, detail="User to follow not found")

    # Проверить, что пользователь не пытается подписаться сам на себя
    if follower.id == followed.id:
        raise HTTPException(status_code=400, detail="Users cannot follow themselves")

    # Добавить запись в таблицу подписок
    follow = Follow(follower_id=follower.id, followed_id=followed.id)

    try:
        db.add(follow)
        db.commit()
        return {"result": True}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You already follow this user")


@app.get("/api/tweets")
def get_user_feed(
    api_key: str = Header(..., alias="api-key"),
    db: Session = Depends(get_db)
):
    try:
        user = get_user_by_api_key(db, api_key)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

                # Находим ID пользователей, на которых подписан текущий пользователь
        followed_users = db.query(Follow.followed_id).filter(Follow.follower_id == user.id).all()
        followed_user_ids = [followed_id for (followed_id,) in followed_users]
        #
        # # Получаем твиты от пользователей, на которых подписан пользователь
        tweets = db.query(Tweet).options(
            joinedload(Tweet.author),
            joinedload(Tweet.attachments),
            joinedload(Tweet.likes).joinedload(Like.user)
        ).filter(Tweet.author_id.in_(followed_user_ids)).all()

        # # Формируем ответ
        tweet_list = []
        for tweet in tweets:
            tweet_list.append({
                "id": tweet.id,
                "content": tweet.tweet_data,
                "attachments": [f"/media/{media.id}" for media in tweet.attachments],
                "author": {
                    "id": tweet.author.id,
                    "name": tweet.author.name,
                },
                "likes": [{"user_id": like.user.id, "name": like.user.name} for like in tweet.likes]
            })

        return {"result": True, "tweets": tweet_list}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"result": False, "error_type": "ServerError", "error_message": str(e)}
        )