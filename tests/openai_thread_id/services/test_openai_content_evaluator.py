from unittest.mock import MagicMock

import pytest

from openai_thread_id.services.openai_content_evaluator import (
    ContentSafeException,
    OpenAIContentEvaluator,
)


@pytest.mark.asyncio
async def test_content_safety_check_input():
    test_data = MagicMock(
        choices=[
            MagicMock(message=MagicMock(content="Test response"), finish_reason="stop")
        ],
        usage=None,
        prompt_filter_results=[
            {
                "content_filter_results": {
                    "hate_speech": {"filtered": False, "severity": "high"},
                }
            }
        ],
    )

    with pytest.raises(ContentSafeException):
        OpenAIContentEvaluator().content_safety_check(response=test_data)


@pytest.mark.asyncio
async def test_content_safety_check_input_filtered():
    test_data = MagicMock(
        choices=[
            MagicMock(message=MagicMock(content="Test response"), finish_reason="stop")
        ],
        usage=None,
        prompt_filter_results=[
            {
                "content_filter_results": {
                    "hate_speech": {"filtered": True, "severity": "low"},
                }
            }
        ],
    )

    with pytest.raises(ContentSafeException):
        OpenAIContentEvaluator().content_safety_check(response=test_data)


@pytest.mark.asyncio
async def test_content_safety_check_output():
    test_data = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Test response"),
                finish_reason="stop",
                model_extra={
                    "content_filter_results": {
                        "hate_speech": {"filtered": False, "severity": "high"},
                    }
                },
            )
        ],
        usage=None,
        prompt_filter_results=[
            {
                "content_filter_results": {
                    "hate_speech": {"filtered": False, "severity": "safe"},
                }
            }
        ],
    )

    with pytest.raises(ContentSafeException):
        OpenAIContentEvaluator().content_safety_check(response=test_data)


@pytest.mark.asyncio
async def test_content_safety_check_input_empty():
    test_data = MagicMock(
        choices=[MagicMock(message=MagicMock(content=""), finish_reason="stop")],
        usage=None,
        prompt_filter_results=[],
    )

    OpenAIContentEvaluator().content_safety_check(response=test_data)
