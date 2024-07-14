from .database import Base
from sqlalchemy import Column, Integer, String, ARRAY


class Tweet(Base):
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True, index=True)
    tweet_data = Column(String, index=True)
    tweet_media_ids = Column(ARRAY(Integer), nullable=True)
