import hashlib

from .repository import UrlRepository


class UrlService:
    def __init__(self, repository: UrlRepository) -> None:
        self.repository = repository

    def create(self, url: str) -> dict[str, str]:
        code = hashlib.sha256(url.encode()).hexdigest()[:7]
        self.repository.save(code, url)
        return {"code": code, "url": url}

    def resolve(self, code: str) -> str:
        return self.repository.get(code)
