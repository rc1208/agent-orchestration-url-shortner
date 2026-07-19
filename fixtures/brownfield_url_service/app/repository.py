class UrlRepository:
    def __init__(self) -> None:
        self.urls: dict[str, str] = {}

    def save(self, code: str, url: str) -> None:
        self.urls[code] = url

    def get(self, code: str) -> str:
        return self.urls[code]
