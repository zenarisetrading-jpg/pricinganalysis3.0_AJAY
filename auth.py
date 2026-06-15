import os

from fastapi import Header, HTTPException, Request


def get_current_client_id(
    request: Request,
    x_client_id: str | None = Header(default=None, alias="X-Client-Id")
) -> str:
    # 1. Try case-insensitive custom header via alias
    # 2. Try query parameter client_id (e.g. if proxy stripped the header)
    # 3. Fallback to default client env variable
    client_id = x_client_id or request.query_params.get("client_id") or os.getenv("DEFAULT_CLIENT_ID")
    
    if not client_id:
        raise HTTPException(
            status_code=401,
            detail="Missing client identity. Set X-Client-Id header or DEFAULT_CLIENT_ID.",
        )
    return client_id
