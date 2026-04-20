from typing import Literal, Protocol

from openai.types.chat import ChatCompletion


class ContentSafeException(Exception):
    pass


class IOpenAIContentEvaluator(Protocol):
    def content_safety_check(
        self,
        response: ChatCompletion,
        threshold: Literal["low", "medium", "high"] = "high",
    ) -> None:
        """
        Perform a content safety check on the given ChatCompletion response.

        :param response: The ChatCompletion response to check.
        :param threshold: The severity threshold for filtering content.
        :raises ContentSafeException: If the content safety check fails.
        """
        ...
