---
title: Token Caching and Cost Optimization in Azure OpenAI Service
description:
  Understand how Azure OpenAI prompt caching works, when cache hits occur, and
  how to structure requests to reduce latency and input token cost.
author: Dennis Seah
ms.date: 2026-04-19
ms.topic: concept
keywords:
  - Azure OpenAI
  - prompt caching
  - token caching
  - cost optimization
  - cached tokens
estimated_reading_time: 5
---

## Introduction

Azure OpenAI's prompt caching feature has been available since late 2024, but
many users still have questions about how it works and how to benefit from it.
This article provides a practical overview of prompt caching, including what it
does, when cache hits occur, and how to structure requests for better reuse. It
does not help in every workload, but when your application sends long requests
with repeated leading context, it can significantly reduce latency and input
token cost.

## Why this matters

Azure OpenAI prompt caching is one of the easiest ways to reduce both latency
and input token cost for long, repetitive requests. Many teams know the feature
exists, but they often misunderstand what is cached, when a cache hit happens,
and why their requests still show `cached_tokens: 0`.

The most important detail is this: Azure OpenAI does not cache the model's final
answer. It caches prompt-prefix computations for supported models when the
beginning of the request is identical across calls. If you structure your
requests well, repeated context such as system instructions, long reference
documents, tool definitions, and stable conversation scaffolding can become much
cheaper to reuse.

## What Azure calls the feature

The official Azure term is _prompt caching_. Many people call it \*token
caching\_, which is understandable, but prompt caching is the more accurate term
because the service is reusing previously processed input prompt work rather
than replaying generated output tokens.

## Which models support prompt caching

According to the Azure documentation, prompt caching is supported for Azure
OpenAI models that are GPT-4o or newer. It applies to supported operations such
as chat completions, completions, responses, and real-time operations.

Prompt caching is enabled by default for supported models. There is currently no
opt-out setting.

For the latest support matrix, refer to the official documentation:
[Azure OpenAI prompt caching](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/prompt-caching).

## How prompt caching actually works

Prompt caching is based on the _beginning_ of the request, not on the request as
a whole in the loose, human sense of "same prompt." To qualify for caching, a
request must meet both of these requirements:

- The prompt must be at least 1,024 tokens long
- The first 1,024 tokens must be identical to a previous request

Azure routes requests using a hash derived from the initial prompt prefix. The
documentation notes that the hash typically uses the first 256 tokens, although
the exact length can vary by model.

After the first 1,024 tokens, cache hits continue in 128-token increments as
long as those additional tokens are also identical.

This has two practical consequences:

- A single character difference early in the prompt can turn a likely cache hit
  into a miss
- Repetitive content should be placed at the beginning of the request, not near
  the end

## What is cached

Azure documents prompt caching support for these request components:

- The full messages array, including system, developer, user, and assistant
  content
- Images in user messages, as long as the `detail` parameter also matches
- Tool definitions used for tool calling
- Structured output schema, which is appended as a prefix to the system message

This means you can benefit from caching even in more advanced scenarios, not
only plain text prompts.

## What is not true about prompt caching

Several common explanations are misleading or incorrect.

Prompt caching does **not** work by storing the final generated response and
returning that response later. The model still produces a fresh response for the
current request.

Prompt caching is **not** best understood as "same API key, same model, same
prompt." The actual trigger is identical leading tokens on supported models,
combined with Azure's cache routing behavior.

Prompt caches are also **not** shared across Azure subscriptions. Azure's
documentation states that caches are not shared between subscriptions.

## How long the cache lives

Prompt caches are temporary. Azure states that caches are typically cleared
within 5 to 10 minutes of inactivity and are always removed within one hour of
the cache's last use.

That means prompt caching is most useful for repeated traffic patterns that
happen close together in time. It is less useful for prompts that are reused
only occasionally across long gaps.

## Does a cache hit return the same response

No, the model generates a new response for each request, even on cache hits. The
cached portion is the prompt processing, not the final answer. Since the model
still produces a fresh response, you can expect variability in the output on
each call, regardless of caching.

There is still a cost associated with generating the response. Prompt caching
reduces repeated input processing cost and latency, but it does not eliminate
output token cost.

## How to verify that caching is working

The easiest way to confirm prompt caching is to inspect the response usage
object. On a cache hit, Azure reports cached prompt reuse in
`prompt_tokens_details.cached_tokens`.

For example:

```json
{
  "usage": {
    "prompt_tokens": 1566,
    "completion_tokens": 1518,
    "total_tokens": 3084,
    "prompt_tokens_details": {
      "cached_tokens": 1408
    }
  }
}
```

If `cached_tokens` is `0`, the request missed the cache. In practice, the most
common causes are:

- The prompt is shorter than 1,024 tokens
- The first 1,024 tokens changed
- Repetitive content appears too late in the request
- Requests are spread too far apart and the cache expired

## How cached tokens are billed

Cached tokens are not universally free. For Standard deployments, Azure bills
cached input tokens at a discount compared to normal input token pricing. For
Provisioned deployments, Azure documentation indicates discounts can be higher,
up to 100 percent for cached input tokens in some cases.

The exact pricing depends on deployment type, region, and model. Pricing can
also change over time, so the correct source of truth is always the current
Azure pricing page and product documentation.

## How to improve cache hit rates

If you want better cost savings, the main optimization is request structure.

Place stable, repeated content at the front of the request. Keep volatile
content, such as the user's latest question, near the end. This pattern gives
Azure the best chance of reusing the expensive prefix computations.

Useful examples of cache-friendly content include:

- Long system or developer instructions
- Repeated policy text
- Shared retrieval context
- Tool definitions
- Structured output schema

If many requests share the same long prefix, consider using the
`prompt_cache_key` parameter. Azure combines this value with the prefix hash to
influence routing and improve cache hit rates. This is especially helpful in
high-volume applications with repeated prompt templates.

> [!TIP] If your application sends large prompts with only small changes at the
> end, move the changing portion as late as possible in the request.

## A practical mental model

Prompt caching works best when you think of your request in two layers:

- A stable prefix that you want Azure to reuse
- A small variable suffix that changes per request

The more expensive and stable your prefix is, the more value you can get from
prompt caching.

## Final takeaway

Prompt caching in Azure OpenAI is real, useful, and often underused. It does not
cache completed answers. It reduces repeated input processing when the leading
portion of the request stays the same. If you design prompts with a stable,
shared prefix and verify results through `cached_tokens`, you can reduce cost
and improve latency without changing model behavior.

For current feature behavior and pricing details, use the official reference:
[Azure OpenAI prompt caching](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/prompt-caching).
