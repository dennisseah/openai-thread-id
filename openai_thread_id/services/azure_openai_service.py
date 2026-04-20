import logging
from dataclasses import dataclass
from typing import Any, Callable

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from lagom.environment import Env
from openai import AsyncAzureOpenAI, BadRequestError
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
)

from openai_thread_id.models.llm_response import LLMResponse
from openai_thread_id.protocols.i_azure_openai_service import (
    IAzureOpenAIService,
)
from openai_thread_id.protocols.i_openai_content_evaluator import (
    IOpenAIContentEvaluator,
)


class AzureOpenAIServiceEnv(Env):
    azure_openai_endpoint: str
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str
    azure_openai_deployed_model_name: str


@dataclass
class AzureOpenAIService(IAzureOpenAIService):
    """
    Azure OpenAI Service implementation.
    """

    env: AzureOpenAIServiceEnv
    content_safety_eval: IOpenAIContentEvaluator

    def __post_init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = self.get_client()

    def get_openai_auth_key(self) -> dict[str, str | Callable[[], str]]:
        if self.env.azure_openai_api_key:
            return {"api_key": self.env.azure_openai_api_key}

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )

        return {"azure_ad_token_provider": token_provider}

    def get_client(self) -> AsyncAzureOpenAI:
        return AsyncAzureOpenAI(
            azure_endpoint=self.env.azure_openai_endpoint,
            api_version=self.env.azure_openai_api_version,
            **self.get_openai_auth_key(),  # type: ignore
        )

    def get_deployed_model_name(self) -> str:
        return self.env.azure_openai_deployed_model_name

    def is_reasoning_model(self) -> bool:
        """Check if the deployed model is a reasoning model.

        Reasoning models (o1, o3, o4-mini, gpt-5, etc.) do not support
        temperature, n > 1, or the system role in messages.
        """
        name = self.env.azure_openai_deployed_model_name.lower()
        return name.startswith(("o1", "o3", "o4", "gpt-5"))

    @staticmethod
    def remap_messages_for_reasoning(
        messages: list[ChatCompletionMessageParam],
    ) -> list[ChatCompletionMessageParam]:
        """Remap 'system' role to 'developer' for reasoning models.

        Reasoning models do not accept the 'system' role and require
        'developer' instead.
        """
        remapped: list[ChatCompletionMessageParam] = []
        for msg in messages:
            if msg.get("role") == "system":
                remapped.append({**msg, "role": "developer"})  # type: ignore
            else:
                remapped.append(msg)
        return remapped

    def collection_results(
        self, responses: ChatCompletion, num_generations: int
    ) -> list[LLMResponse]:
        self.content_safety_eval.content_safety_check(responses)

        usages = responses.usage.model_dump() if responses.usage else {}
        token_usages: dict[str, int | dict[str, int]] = {
            k: v for k, v in usages.items() if isinstance(v, int)
        }
        token_usages["completion_tokens"] = int(
            usages.get("completion_tokens", 0) / num_generations
        )
        for detail in ["completion_tokens_details", "prompt_tokens_details"]:
            token_usages[detail] = usages[detail] if detail in usages else {}

        results = []
        for choice in responses.choices:
            results.append(
                LLMResponse(
                    content=choice.message.content if choice.message else "",
                    finish_reason=choice.finish_reason,
                    usages=token_usages,
                )
            )
        return results

    def _handle_content_filter_error(self, e: BadRequestError) -> list[LLMResponse]:
        """Extract content filter details from a BadRequestError and return
        an LLMResponse with content_filtered populated."""
        body = e.body
        content_filter_result = ""

        if isinstance(body, dict):
            inner = body.get("innererror") or {}
            cfr = inner.get("content_filter_result", {})
            # collect the names of filters that were triggered
            triggered = [
                name
                for name, detail in cfr.items()
                if isinstance(detail, dict)
                and (detail.get("filtered") or detail.get("detected"))
            ]
            content_filter_result = (
                ", ".join(triggered)
                if triggered
                else body.get("code", "content_filter")
            )

        self.logger.warning(
            f"Content filtered by Azure OpenAI: {content_filter_result}"
        )

        return [
            LLMResponse(
                content=None,
                finish_reason="content_filter",
                usages={},
                content_filtered=content_filter_result,
            )
        ]

    async def chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 1.0,
        num_generations: int = 1,
    ) -> list[LLMResponse]:
        self.logger.debug("[BEGIN] chat_completion")

        self.client = self.get_client()

        is_reasoning = self.is_reasoning_model()

        kwargs: dict[str, Any] = {
            "model": self.env.azure_openai_deployed_model_name,
            "messages": (
                self.remap_messages_for_reasoning(messages)
                if is_reasoning
                else messages
            ),
        }

        if not is_reasoning:
            kwargs["temperature"] = temperature
            kwargs["n"] = num_generations

        try:
            response = await self.client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            return self._handle_content_filter_error(e)

        self.logger.debug("[COMPLETED] chat_completion")
        return self.collection_results(response, 1 if is_reasoning else num_generations)
