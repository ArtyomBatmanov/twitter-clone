from fastapi import Header, HTTPException

def get_api_key(api_key: str = Header(None)) -> str:
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key missing")
    return api_key
