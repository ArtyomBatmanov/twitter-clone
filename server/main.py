from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from schemas import TweetCreate, TweetResponse, MediaUploadResponse
from database import get_db, SessionLocal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from crud import add_tweet, get_tweet, add_like, get_user_profile
from utils import get_user_by_api_key
from starlette.responses import FileResponse
from models import User, Media, Follow, Like, Tweet
import shutil
import os

app = FastAPI()

# app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../client/static")), name="static")
# app.mount("/js", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../client/static/js")), name="js")
# app.mount("/css", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../client/static/css")), name="css")


# app.mount("/static", StaticFiles(directory=".../client/static"), name="static")
# app.mount("/js", StaticFiles(directory=".../client/static/js"), name="js")
# app.mount("/css", StaticFiles(directory=".../client/static/css"), name="css")


TEST_USER_ID = 1

def get_current_user(api_key: str = Header(...), db: Session = Depends(get_db)):
    """
    Получить текущего пользователя по API-ключу.1
    """
    user = db.query(User).filter(User.api_key == api_key).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user


@app.get("/")
def read_main():
    return FileResponse("/client/static/index.html")


@app.post("/api/tweets", response_model=TweetResponse, summary="Создать твит",
          description="Создаёт новый твит для пользователя.")
def create_tweet(
        tweet: TweetCreate,
        api_key: str = Header(..., alias="api-key"),
        db: Session = Depends(get_db),
):
    """
    Этот эндпоинт создаёт новый твит. Пользователь должен быть авторизован через API-ключ.
    """
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db_tweet = add_tweet(db=db, tweet=tweet, user_id=user.id)
    return db_tweet


@app.post("/api/medias", response_model=MediaUploadResponse, summary="Загрузить медиафайл",
          description="Загружает медиафайл для пользователя.")
def upload_media(
        api_key: str = Header(..., alias="api-key"),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    """
    Эндпоинт для загрузки медиафайла.
    """
    user = get_user_by_api_key(db, api_key)

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media = Media(file_path=file_path)
    db.add(media)
    db.commit()
    db.refresh(media)

    return MediaUploadResponse(result=True, media_id=media.id)


@app.delete("/api/tweets/{id}", summary="Удалить твит",
            description="Удаляет указанный твит, если пользователь является его автором.")
def delete_tweet(
        id: int, api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)
):
    """
    Удаление твита по его ID. Только автор твита может его удалить.
    """
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweet = get_tweet(db, id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    if tweet.author_id != user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this tweet"
        )

    db.delete(tweet)
    db.commit()

    return {"result": True}


@app.post("/api/tweets/{id}/likes", summary="Лайкнуть твит", description="Лайкнуть указанный твит.")
def like_tweet(
        id: int, api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)
):
    """
    Лайкнуть твит по его ID.
    """
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweet = get_tweet(db, id)
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    add_like(db=db, user_id=user.id, tweet_id=tweet.id)

    return {"result": True}


@app.post("/api/users/{id}/follow", summary="Подписаться на пользователя",
          description="Подписаться на указанного пользователя.")
def follow_user(
        id: int, api_key: str = Header(..., alias="api-key"), db: Session = Depends(get_db)
):
    """
    Подписаться на пользователя по его ID. Нельзя подписаться на самого себя.
    """
    follower = get_user_by_api_key(db, api_key)
    if not follower:
        raise HTTPException(status_code=404, detail="User not found")

    followed = db.query(User).filter(User.id == id).first()
    if not followed:
        raise HTTPException(status_code=404, detail="User to follow not found")

    if follower.id == followed.id:
        raise HTTPException(status_code=400, detail="Users cannot follow themselves")

    follow = Follow(follower_id=follower.id, followed_id=followed.id)

    try:
        db.add(follow)
        db.commit()
        return {"result": True}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="You already follow this user")


@app.get("/api/tweets")
def get_user_feed(request: Request, db: Session = Depends(get_db)):
    """
    Получить список твитов по рекмоендациям.
    """
    try:
        user = request.state.user

        followed_users = (
            db.query(Follow.followed_id).filter(Follow.follower_id == user.id).all()
        )
        followed_user_ids = [followed_id for (followed_id,) in followed_users]

        tweets = (
            db.query(Tweet)
            .options(
                joinedload(Tweet.author),
                joinedload(Tweet.attachments),
                joinedload(Tweet.likes).joinedload(Like.user),
            )
            .filter(Tweet.author_id.in_(followed_user_ids))
            .all()
        )

        tweet_list = []
        for tweet in tweets:
            tweet_list.append(
                {
                    "id": tweet.id,
                    "content": tweet.tweet_data,
                    "attachments": [
                        f"/media/{media.id}" for media in tweet.attachments
                    ],
                    "author": {
                        "id": tweet.author.id,
                        "name": tweet.author.name,
                    },
                    "likes": [
                        {"user_id": like.user.id, "name": like.user.name}
                        for like in tweet.likes
                    ],
                }
            )

        return {"result": True, "tweets": tweet_list}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "result": False,
                "error_type": "ServerError",
                "error_message": str(e),
            },
        )


@app.get("/login")
def get_user_me(
        request: Request,
        # api_key: str = Header(..., alias="api-key"),
        db: Session = Depends(get_db)
):
    """
    Авторизация пользователя по API-key
    """
    api_key = request.headers.get('api-key', 'test')
    user = get_user_by_api_key(db, api_key)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data, followers, following = get_user_profile(db, user.id)

    response = {
        "result": "true",
        "user": {
            "id": user_data.id,
            "name": user_data.name,
            "followers": [
                {"id": follower.id, "name": follower.name} for follower in followers
            ],
            "following": [
                {"id": followed.id, "name": followed.name} for followed in following
            ],
        },
    }

    return response


@app.get("/api/users/{id}")
def get_user_by_id(id: int, db: Session = Depends(get_db)):
    """
    Получить информацию о пользователе по ID
    """
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    followers = (
        db.query(User)
        .join(Follow, Follow.follower_id == User.id)
        .filter(Follow.followed_id == id)
        .all()
    )

    following = (
        db.query(User)
        .join(Follow, Follow.followed_id == User.id)
        .filter(Follow.follower_id == id)
        .all()
    )

    response = {
        "result": "true",
        "user": {
            "id": user.id,
            "name": user.name,
            "followers": [
                {"id": follower.id, "name": follower.name} for follower in followers
            ],
            "following": [
                {"id": followed.id, "name": followed.name} for followed in following
            ],
        },
    }

    return response


@app.middleware("http")
async def check_user_middleware(request: Request, call_next):
    db: Session = SessionLocal()

    try:
        if request.url.path.startswith("/api"):
            api_key = request.headers.get("Api-Key")

            if api_key:
                user = db.query(User).filter(User.api_key == api_key).first()
                if not user:
                    return JSONResponse(
                        status_code=404,
                        content={
                            "result": False,
                            "error_type": "NotFound",
                            "error_message": "User not found",
                        },
                    )
            else:
                user = db.query(User).filter(User.id == TEST_USER_ID).first()
                if not user:
                    return JSONResponse(
                        status_code=500,
                        content={
                            "result": False,
                            "error_type": "ServerError",
                            "error_message": "Test user not found in the database",
                        },
                    )

            request.state.user = user

        response = await call_next(request)

    finally:
        db.close()

    return response
