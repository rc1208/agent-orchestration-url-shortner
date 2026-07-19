from fastapi import FastAPI

from .repository import UrlRepository
from .schemas import CreateUrl
from .service import UrlService

app = FastAPI()
service = UrlService(UrlRepository())


@app.post("/urls")
def create_url(payload: CreateUrl) -> dict[str, str]:
    return service.create(str(payload.url))


@app.get("/{code}")
def resolve_url(code: str) -> dict[str, str]:
    return {"url": service.resolve(code)}
