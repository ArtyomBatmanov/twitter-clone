from sqlalchemy.orm import Session
from .models import User, Tweet
from .schemas import TweetCreate


def create_tweet(db: Session, tweet: TweetCreate, user_id: int):
    db_tweet = Tweet(content=tweet.content, author_id=user_id)
    db.add(db_tweet)
    db.commit()
    db.refresh(db_tweet)
    return db_tweet


def get_tweet(db: Session, tweet_id: int):
    return db.query(Tweet).filter(Tweet.id == tweet_id).first()


def delete_tweet(db: Session, tweet_id: int, user_id: int):
    db_tweet = db.query(Tweet).filter(Tweet.id == tweet_id, Tweet.author_id == user_id).first()
    if db_tweet:
        db.delete(db_tweet)
        db.commit()
    return db_tweet


def get_user_by_api_key(db: Session, api_key: str) -> User:
    return db.query(User).filter(User.api_key == api_key).first()
