from openai_thread_id.models.llm_response import LLMResponse


def test_token_usage():
    response = LLMResponse(
        content="Test content",
        finish_reason="stop",
        usages={"prompt_tokens": 10, "completion_tokens": 15, "total_tokens": 25},
    )
    assert response.token_usages() == 50  # 10 + 15 + 25

    response_no_usage = LLMResponse(
        content="Test content",
        finish_reason="stop",
        usages={},
    )
    assert response_no_usage.token_usages() == 0
