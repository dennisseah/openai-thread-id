from typing import Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import BadRequestError
from pytest_mock import MockerFixture

from openai_thread_id.services.azure_openai_service import AzureOpenAIService


class MockBadRequestError(BadRequestError):
    def __init__(self, body: object):
        Exception.__init__(self, "bad request")
        self.body = body


@pytest.fixture
def fn_mock_service(mocker: MockerFixture) -> Callable[[bool], AzureOpenAIService]:
    def wrapper(with_api_key: bool) -> AzureOpenAIService:
        patched_azure_openai = mocker.patch(
            "openai_thread_id.services.azure_openai_service.AsyncAzureOpenAI",
            autospec=True,
        )

        mock_cred = MagicMock()
        mock_cred.get_token.return_value = MagicMock(
            token="mock_token",
            scope="https://example.com/.default",
        )
        mocker.patch(
            "openai_thread_id.services.azure_openai_service.DefaultAzureCredential",
            return_value=mock_cred,
        )

        env = MagicMock()
        if not with_api_key:
            env.azure_openai_api_key = None
        svc = AzureOpenAIService(env=env, content_safety_eval=MagicMock())
        patched_azure_openai.assert_called_once()
        return svc

    return wrapper


def test_get_client(
    fn_mock_service: Callable[[bool], AzureOpenAIService], mocker: MockerFixture
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore
    assert mock_service.client is not None


def test_get_client_without_api_key(
    fn_mock_service: Callable[[bool], AzureOpenAIService], mocker: MockerFixture
):
    mock_service = fn_mock_service(with_api_key=False)  # type: ignore
    assert mock_service.client is not None


def test_get_deployed_model_name(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore
    mock_service.env.azure_openai_deployed_model_name = "test-model"

    model_name = mock_service.get_deployed_model_name()
    assert model_name == "test-model"


@pytest.mark.asyncio
async def test_chat_completion(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore
    mock_service.env.azure_openai_deployed_model_name = "gpt-4.1"
    mock_service.client.chat.completions = MagicMock()
    mock_service.client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Test response"), finish_reason="stop"
                )
            ],
            usage=None,
        )
    )
    messages = [{"role": "user", "content": "Test message"}]
    responses = await mock_service.chat_completion(messages)
    assert responses[0].content == "Test response"
    mock_service.content_safety_eval.content_safety_check.assert_called_once()


@pytest.mark.asyncio
async def test_chat_completion_reasoning_model(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    """Reasoning models (o-series) should not receive temperature or n params
    and should remap system -> developer role."""
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore
    mock_service.env.azure_openai_deployed_model_name = "o4-mini"

    mock_create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Reasoning response"),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )
    )
    mock_service.client.chat.completions = MagicMock()
    mock_service.client.chat.completions.create = mock_create

    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Test message"},
    ]
    responses = await mock_service.chat_completion(messages, temperature=0.5)

    assert responses[0].content == "Reasoning response"

    # Verify temperature and n were NOT passed
    call_kwargs = mock_create.call_args[1]
    assert "temperature" not in call_kwargs
    assert "n" not in call_kwargs

    # Verify system role was remapped to developer
    sent_messages = call_kwargs["messages"]
    assert sent_messages[0]["role"] == "developer"
    assert sent_messages[0]["content"] == "You are helpful"
    assert sent_messages[1]["role"] == "user"


def test_handle_content_filter_error_collects_triggered_filters(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore

    error = MockBadRequestError(
        {
            "innererror": {
                "content_filter_result": {
                    "hate": {"filtered": True},
                    "jailbreak": {"detected": True},
                    "violence": {"filtered": False},
                }
            }
        }
    )

    responses = mock_service._handle_content_filter_error(error)

    assert len(responses) == 1
    assert responses[0].content is None
    assert responses[0].finish_reason == "content_filter"
    assert responses[0].content_filtered == "hate, jailbreak"


def test_handle_content_filter_error_falls_back_to_error_code(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore

    error = MockBadRequestError(
        {
            "code": "ResponsibleAIPolicyViolation",
            "innererror": {"content_filter_result": {}},
        }
    )

    responses = mock_service._handle_content_filter_error(error)

    assert len(responses) == 1
    assert responses[0].content_filtered == "ResponsibleAIPolicyViolation"


@pytest.mark.asyncio
async def test_chat_completion_returns_filtered_response_on_bad_request(
    fn_mock_service: Callable[[bool], AzureOpenAIService],
):
    mock_service = fn_mock_service(with_api_key=True)  # type: ignore
    mock_service.env.azure_openai_deployed_model_name = "gpt-4.1"
    mock_service.client.chat.completions = MagicMock()
    mock_service.client.chat.completions.create = AsyncMock(
        side_effect=MockBadRequestError(
            {"innererror": {"content_filter_result": {"self_harm": {"filtered": True}}}}
        )
    )

    messages = [{"role": "user", "content": "Test message"}]
    responses = await mock_service.chat_completion(messages)

    assert len(responses) == 1
    assert responses[0].finish_reason == "content_filter"
    assert responses[0].content_filtered == "self_harm"
    mock_service.content_safety_eval.content_safety_check.assert_not_called()
