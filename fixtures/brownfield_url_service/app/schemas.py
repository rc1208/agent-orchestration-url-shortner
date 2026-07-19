from pydantic import BaseModel, HttpUrl


class CreateUrl(BaseModel):
    url: HttpUrl
