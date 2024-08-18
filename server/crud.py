from sqlalchemy.orm import Session
from .models import User, Tweet
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



