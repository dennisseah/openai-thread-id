"""Defines our top level DI container.
Utilizes the Lagom library for dependency injection, see more at:

- https://lagom-di.readthedocs.io/en/latest/
- https://github.com/meadsteve/lagom
"""

from dotenv import load_dotenv
from lagom import Container, dependency_definition

from openai_thread_id.protocols.i_azure_openai_service import IAzureOpenAIService
from openai_thread_id.protocols.i_openai_content_evaluator import (
    IOpenAIContentEvaluator,
)

load_dotenv(dotenv_path=".env")


container = Container()
"""The top level DI container for our application."""


# Register our dependencies ------------------------------------------------------------


@dependency_definition(container, singleton=True)
def azure_openai_service() -> IAzureOpenAIService:
    from openai_thread_id.services.azure_openai_service import (
        AzureOpenAIService,
    )

    return container[AzureOpenAIService]


@dependency_definition(container, singleton=True)
def openai_content_evaluator() -> IOpenAIContentEvaluator:
    from openai_thread_id.services.openai_content_evaluator import (
        OpenAIContentEvaluator,
    )

    return container[OpenAIContentEvaluator]
