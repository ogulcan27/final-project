---
name: openrouter-inference
description: Use this to write code to call an LLM using LiteLLM and OpenRouter with the free NVIDIA Nemotron 3 Super model and Structured Outputs
---

# Calling an LLM via OpenRouter

These instructions allow you to write code to call a free LLM on OpenRouter with Structured Outputs.
This method uses LiteLLM and OpenRouter.

## Setup

The OPENROUTER_API_KEY must be set in the .env file and loaded in as an environment variable.

The uv project must include litellm and pydantic.
`uv add litellm pydantic`

## Code snippets

Use code like these examples in order to call the model.

### Imports and constants

`require_parameters` makes OpenRouter route only to endpoints that support every parameter sent (e.g. `response_format`).

```python
from litellm import completion
MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
EXTRA_BODY = {"provider": {"require_parameters": True}}
```

### Code to call for a text response

```python
response = completion(model=MODEL, messages=messages, extra_body=EXTRA_BODY)
result = response.choices[0].message.content
```

### Code to call for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass, extra_body=EXTRA_BODY)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

## Limits

- Free models: 50 requests/day on a free-tier key, rate limited, prompts may be logged by the provider.
- Use `LLM_MOCK=true` for tests and development to avoid spending the daily quota.
