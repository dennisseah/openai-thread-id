from typing import Protocol

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletionMessageParam

from openai_thread_id.models.llm_response import LLMResponse


class IAzureOpenAIService(Protocol):
    def get_client(self) -> AsyncAzureOpenAI:
        """
        Get the Azure OpenAI client.

        :return: An instance of AsyncAzureOpenAI.
        """
        ...

    def get_deployed_model_name(self) -> str:
        """
        Get the name of the deployed model.

        :return: The name of the deployed model.
        """
        ...

    async def chat_completion(
        self,
        messages: list[ChatCompletionMessageParam],
        temperature: float = 1.0,
        num_generations: int = 1,
    ) -> list[LLMResponse]:
        """
        Perform a chat completion using the Azure OpenAI client.

        :param messages: The messages to send in the chat completion.
        :param temperature: The temperature for the completion.
        :param num_generations: The number of generations to produce.
        :return: The content of the response message.
        """
        ...
