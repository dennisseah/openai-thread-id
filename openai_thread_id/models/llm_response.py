from typing import Any

from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str | None
    finish_reason: str
    usages: dict[str, Any]
    content_filtered: str | None = None

    def token_usages(self) -> int:
        return 0 if self.usages is None else sum(*[list(self.usages.values())])
