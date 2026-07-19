from app.repository import UrlRepository
from app.service import UrlService


def test_create_and_resolve() -> None:
    service = UrlService(UrlRepository())
    created = service.create("https://example.com")
    assert service.resolve(created["code"]) == "https://example.com"
