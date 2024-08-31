from pydantic import BaseModel
from typing import List, Optional


class TweetCreate(BaseModel):
    tweet_data: str
    tweet_media_ids: list[int] = []


class Tweet(BaseModel):
    id: int
    tweet_data: str
    author_id: int

    class Config:
        from_attributes = True


class TweetResponse(BaseModel):
    id: int
    tweet_data: str
    tweet_media_ids: Optional[List[int]]

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    result: bool
    media_id: int
