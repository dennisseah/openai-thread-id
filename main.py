import asyncio
import json
from pathlib import Path

from openai.types.chat import ChatCompletionMessageParam

from openai_thread_id.hosting import container
from openai_thread_id.protocols.i_azure_openai_service import IAzureOpenAIService


async def main():
    # fetch input text from test.txt
    input_text = (Path(__file__).parent / "test.txt").read_text()

    openai_svc = container[IAzureOpenAIService]

    messages: list[ChatCompletionMessageParam] = [
        {
            "role": "system",
            "content": "You are a helpful assistant, summarize the user input",
        },
        {"role": "user", "content": input_text},
    ]

    result = await openai_svc.chat_completion(messages=messages)
    print(json.dumps(result[0].usages, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
