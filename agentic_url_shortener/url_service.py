import secrets
import string
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from .database import Database


class UrlError(Exception):
    code = "URL_ERROR"
    status_code = 400


class AliasConflict(UrlError):
    code = "ALIAS_CONFLICT"
    status_code = 409


class UrlNotFound(UrlError):
    code = "URL_NOT_FOUND"
    status_code = 404


class UrlExpired(UrlError):
    code = "URL_EXPIRED"
    status_code = 410


@dataclass(frozen=True)
class ShortUrl:
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    redirect_count: int
    last_accessed_at: datetime | None
    is_active: bool

    def as_dict(self) -> dict:
        return asdict(self)


def _now() -> datetime:
    return datetime.now(UTC)


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class UrlService:
    alphabet = string.ascii_letters + string.digits

    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, url: str, custom_alias: str | None, expires_at: datetime | None) -> ShortUrl:
        if expires_at and expires_at <= _now():
            raise ValueError("Expiration must be in the future")
        for _ in range(5):
            code = custom_alias or "".join(secrets.choice(self.alphabet) for _ in range(7))
            try:
                with self.database.connect() as connection:
                    connection.execute(
                        "INSERT INTO short_urls(short_code, original_url, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?)",
                        (code, url, _now().isoformat(), expires_at.isoformat() if expires_at else None),
                    )
                return self.get(code)
            except Exception as error:
                import sqlite3

                if not isinstance(error, sqlite3.IntegrityError):
                    raise
                if custom_alias:
                    raise AliasConflict(f"Alias '{code}' already exists") from error
        raise AliasConflict("Unable to allocate a unique short code")

    def get(self, code: str) -> ShortUrl:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM short_urls WHERE short_code = ? AND is_active = 1", (code,)
            ).fetchone()
        if not row:
            raise UrlNotFound(code)
        created_at = _parse(row["created_at"])
        if created_at is None:
            raise RuntimeError("Persisted URL is missing created_at")
        return ShortUrl(
            short_code=row["short_code"], original_url=row["original_url"],
            created_at=created_at, expires_at=_parse(row["expires_at"]),
            redirect_count=row["redirect_count"], last_accessed_at=_parse(row["last_accessed_at"]),
            is_active=bool(row["is_active"]),
        )

    def resolve(self, code: str) -> ShortUrl:
        item = self.get(code)
        if item.expires_at and item.expires_at <= _now():
            raise UrlExpired(code)
        now = _now().isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE short_urls SET redirect_count = redirect_count + 1, last_accessed_at = ? "
                "WHERE short_code = ?", (now, code),
            )
        return self.get(code)

    def delete(self, code: str) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute("UPDATE short_urls SET is_active = 0 WHERE short_code = ?", (code,))
        if cursor.rowcount == 0:
            raise UrlNotFound(code)
