from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from .models import User, Tweet, Like
from .schemas import TweetCreate, TweetResponse


def add_tweet(db: Session, tweet: TweetCreate, user_id: int):
    db_tweet = Tweet(tweet_data=tweet.tweet_data, author_id=user_id)
    db.add(db_tweet)
    db.commit()
    db.refresh(db_tweet)
    media_ids = tweet.tweet_media_ids if tweet.tweet_media_ids else []

    # Возврат данных в формате TweetResponse
    return TweetResponse(
        id=db_tweet.id,
        tweet_data=db_tweet.tweet_data,  # Используйте правильное поле
        author_id=db_tweet.author_id,
        tweet_media_ids=media_ids
    )


def get_tweet(db: Session, tweet_id: int):
    return db.query(Tweet).filter(Tweet.id == tweet_id).first()


def delete_tweet(db: Session, tweet_id: int, user_id: int):
    db_tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.author_id == user_id).first()
    if db_tweet:
        db.delete(db_tweet)
        db.commit()
    return db_tweet


def add_like(db: Session, user_id: int, tweet_id: int):
    like = Like(user_id=user_id, tweet_id=tweet_id)
    db.add(like)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # Если лайк уже существует, откатываем транзакцию
        raise HTTPException(status_code=400, detail="Like already exists")
    db.refresh(like)
    return like
