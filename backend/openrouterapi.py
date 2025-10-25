import requests
import json
import asyncio
import aiohttp
import os
import dotenv
from typing import List, Dict, Any
from functools import wraps

dotenv.load_dotenv(override=True)


def retry(max_retries=3):
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    print(f"Error in {func.__name__}: {e}. Retry {retries}/{max_retries}")
            return func(*args, **kwargs)  # Last attempt
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    print(f"Error in {func.__name__}: {e}. Retry {retries}/{max_retries}")
            return await func(*args, **kwargs)  # Last attempt
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@retry(max_retries=3)
def call(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-4.1",
    temperature: float = 0.7,
    max_tokens: int = 512,
    json_mode: bool = False,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(payload)
    )
    
    response_json = response.json()

    print(response_json)

    content = response_json["choices"][0]["message"]["content"]
    if json_mode:
        content = json.loads(content)
    
    return {
        "content": content,
        "completion_tokens": response_json["usage"]['completion_tokens']
    }


@retry(max_retries=3)
async def acall(
    api_key: str,
    messages: List[Dict[str, str]],
    model: str = "openai/gpt-4.1",
    temperature: float = 0.7,
    max_tokens: int = 512,
    json_mode: bool = False,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            response_json = await response.json()
            
            content = response_json["choices"][0]["message"]["content"]
            if json_mode:
                content = json.loads(content)
            
            return {
                "content": content,
                "completion_tokens": response_json["usage"]['completion_tokens']
            }


if __name__ == "__main__":
    api_key = os.getenv("OPENROUTER_API_KEY")
    messages = [{"role": "user", "content": "What is the meaning of life? 1 simple sentence 10 words or less. Return a json object with the answer."}]
    
    response = call(api_key=api_key, messages=messages, json_mode=True)
    print(response)
    
    async def test_async():
        response = await acall(api_key=api_key, messages=messages, json_mode=True)
        print(response)
    
    asyncio.run(test_async())
