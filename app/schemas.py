from pydantic import BaseModel

class TweetCreate(BaseModel):
    content: str

class Tweet(BaseModel):
    id: int
    content: str
    author_id: int

    class Config:
        from_attributes = True

