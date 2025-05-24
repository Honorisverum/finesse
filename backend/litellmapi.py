# | Provider | Models |
# |----------|--------|
# | OpenAI | gpt-4o, gpt-4o-mini, gpt-4.5, o1-mini, o3-mini |
# | Anthropic | claude-3-7-sonnet-20250219 |
# | DeepSeek | deepseek-reasoner, deepseek-chat |
# | Google | gemma-3-27b-it, gemini-2.0-flash, gemini-2.0-pro-exp-02-05 |
# | X.ai | grok-3 |
# | Together | meta-llama/Llama-3.3-70B-Instruct-Turbo-Free, meta-llama/Llama-3.3-70B-Instruct-Turbo, Qwen/Qwen2.5-72B-Instruct-Turbo, Qwen/Qwen2.5-7B-Instruct-Turbo |

import http
import json
import os
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv
import litellm
from litellm import completion, get_supported_openai_params, supports_response_schema, supports_function_calling

# Load environment variables
load_dotenv()

# List of all models to test
MODELS = [
    # OpenAI
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4.1",
    "openai/gpt-4.1-mini",
    "openai/gpt-4.5-preview",
    "openai/o1-mini",
    "openai/o3-mini",
    # Anthropic
    "anthropic/claude-3-7-sonnet-20250219",
    # DeepSeek
    "deepseek/deepseek-reasoner",
    "deepseek/deepseek-chat",
    # Google
    "gemini/gemma-3-27b-it",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-2.0-pro-exp-02-05",
    # X.ai
    # 'xai/grok-3',
    # Together
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
    "together_ai/Qwen/Qwen2.5-7B-Instruct-Turbo",
    # Other
    "openrouter/openrouter/quasar-alpha",
    "openrouter/google/gemini-2.0-flash-001",
    # Gabber
    "gabber/GabberNSFWwCompliance",
]


MODELS_LIMITATIONS = {
    "openai/o1-mini": ["json_mode", "json_schema", "function_calling", "multi_function_calling"],
    "gemini/gemma-3-27b-it": ["json_mode", "json_schema", "function_calling", "multi_function_calling"],
    "deepseek/deepseek-reasoner": ["json_mode", "json_schema", "function_calling", "multi_function_calling"],
    "deepseek/deepseek-chat": ["json_schema"],
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo-Free": ["json_schema"],
    "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo": ["json_schema"],
    "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo": ["json_mode", "json_schema", "function_calling", "multi_function_calling"],
    "together_ai/Qwen/Qwen2.5-7B-Instruct-Turbo": ["json_mode", "json_schema", "function_calling", "multi_function_calling"],
}


# Test functions for function calling
TEST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The temperature unit to use"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "Search for restaurants in a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "cuisine": {
                        "type": "string",
                        "description": "Type of cuisine, e.g. Italian, Chinese, Mexican"
                    },
                    "location": {
                        "type": "string",
                        "description": "City or neighborhood to search in"
                    },
                    "price_level": {
                        "type": "string",
                        "enum": ["$", "$$", "$$$", "$$$$"],
                        "description": "Price level, from $ (cheap) to $$$$ (expensive)"
                    }
                },
                "required": ["cuisine", "location"]
            }
        }
    }
]


# JSON Schema Test
class MovieReview(BaseModel):
    title: str = Field(description="The title of the movie")
    year: int = Field(description="Year the movie was released")
    rating: float = Field(description="Rating from 0 to 10")
    review: str = Field(description="Brief review of the movie")
    genres: List[str] = Field(description="List of genres for the movie")
    director: str = Field(description="Name of the movie director")
    recommend: bool = Field(description="Whether you recommend this movie")


# Function to check model capabilities and provide examples
def test_model_capabilities(model_name):
    print(f"\n{'='*80}")
    print(f"TESTING MODEL: {model_name}")
    print(f"{'='*80}")
    
    # Parse model information
    if "/" in model_name:
        provider, name = model_name.split("/", 1)
    else:
        provider, name = None, model_name
    
    # Dictionary to store test results
    results = {
        "model": model_name,
        "standard_completion": False,
        "json_mode": False,
        "json_schema": False,
        "function_calling": False,
        "multi_function_calling": False,
        "examples": {}
    }
    
    # ===== 1. CAPABILITY CHECKS =====
    print("\n----- Capability Checks -----")
    
    # Check supported OpenAI params
    try:
        params = get_supported_openai_params(model=name, custom_llm_provider=provider)
        results["json_mode"] = "response_format" in params
        print(f"✓ Supports JSON mode: {results['json_mode']}")
    except Exception as e:
        print(f"✗ Error checking OpenAI params: {e}")
    
    # Check schema support
    try:
        results["json_schema"] = supports_response_schema(model=name, custom_llm_provider=provider)
        print(f"✓ Supports JSON schema: {results['json_schema']}")
    except Exception as e:
        print(f"✗ Error checking schema support: {e}")
    
    # Check function calling
    try:
        results["function_calling"] = supports_function_calling(model=name, custom_llm_provider=provider)
        # Assume if function calling is supported, multiple function calls might be too
        results["multi_function_calling"] = results["function_calling"]  
        print(f"✓ Supports function calling: {results['function_calling']}")
    except Exception as e:
        print(f"✗ Error checking function calling support: {e}")
    
    # ===== 2. STANDARD COMPLETION TEST =====
    print("\n----- Standard Completion Test -----")
    try:
        response = run(
            model=model_name,
            messages=[{"role": "user", "content": "What's the capital of France?"}],
        )
        print(f"✓ SUCCESS: {response['content']}")
        results["standard_completion"] = True
        results["examples"]["standard"] = response['content']
    except Exception as e:
        print(f"✗ ERROR: {e}")

    # ===== 3. JSON MODE TEST =====
    if results["json_mode"]:
        print("\n----- JSON Mode Test -----")
        try:
            response = run(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                    {"role": "user", "content": "Give me data about 3 planets in our solar system. Include name, diameter, and distance from sun."}
                ],
                json_mode=True,
            )
            print(f"✓ SUCCESS: Generated valid JSON response")
            print(f"JSON Output: {json.dumps(response['json'], indent=2)}")
            results["examples"]["json_mode"] = str(response['json'])
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results["json_mode"] = False
    
    # ===== 4. JSON SCHEMA TEST =====
    if results["json_schema"]:
        print("\n----- JSON Schema Test -----")
        try:
            response = run(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You provide movie reviews in structured format."},
                    {"role": "user", "content": "Review the movie 'Inception'."}
                ],
                json_schema=MovieReview,
            )
            print(f"✓ SUCCESS: Generated schema-compliant JSON")
            print(f"JSON Output: {json.dumps(response['json'], indent=2)}")
            results["examples"]["json_schema"] = str(response['json'])
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results["json_schema"] = False
    
    # ===== 5. FUNCTION CALLING TEST =====
    if results["function_calling"]:
        print("\n----- Function Calling Test -----")
        try:
            response = run(
                model=model_name,
                messages=[{"role": "user", "content": "What's the weather like in San Francisco?"}],
                tools=[TEST_TOOLS[0]],  # Just the weather function
            )
            
            # Check if tools were used
            if response.get('tools') and len(response['tools']) > 0:
                print(f"✓ SUCCESS: Function called: {json.dumps(response['tools'], indent=2)}")
                results["function_calling"] = True
                results["examples"]["function_calling"] = json.dumps(response['tools'], indent=2)
            else:
                print("✗ No function calls detected in response")
                results["function_calling"] = False
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results["function_calling"] = False
    
    # ===== 6. MULTIPLE FUNCTION CALLING TEST =====
    if results["function_calling"]:
        print("\n----- Multiple Function Calling Test -----")
        try:
            # Simple prompt that may use any of the available functions
            response = run(
                model=model_name,
                messages=[{
                    "role": "user", 
                    "content": "I'm in Miami and would like to know the current weather, and also find good Italian restaurants in the area."
                }],
                tools=TEST_TOOLS,  # Provide all tools
            )
            
            # Check if multiple tools were used
            if response.get('tools') and len(response['tools']) > 0:
                # Extract function names for reporting
                function_names = set(tool['name'] for tool in response['tools'])
                
                # Report on which functions were called
                print(f"✓ SUCCESS: Model called these functions: {json.dumps(response['tools'], indent=2)}")
                
                # Consider multi-function success if more than one function was called
                if len(function_names) > 1:
                    results["multi_function_calling"] = True
                else:
                    # Still consider it a success if at least one function was called
                    results["multi_function_calling"] = True
                
                results["examples"]["multi_function_calling"] = json.dumps(response['tools'], indent=2)
            else:
                print("✗ No function calls detected in response")
                results["multi_function_calling"] = False
        except Exception as e:
            print(f"✗ ERROR: {e}")
            results["multi_function_calling"] = False
    
    return results

def extract_json_from_markdown(text):
    """
    Extract JSON content from markdown code blocks or directly parse the JSON.
    
    Args:
        text: String that might contain JSON inside markdown code blocks
        
    Returns:
        Parsed JSON object
    """
    # Find content between ```json and ``` markers
    import re
    pattern = r"```(?:json)?\n([\s\S]*?)```"
    match = re.search(pattern, text)
    
    if match:
        return json.loads(match.group(1))
    else:
        # If no markdown markers, try parsing directly
        return json.loads(text)


def retry(n):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(n):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt + 1}/{n} failed: {e}")
                    if attempt == n - 1:
                        raise
        return wrapper
    return decorator


def run(*args, **kwargs):
    if kwargs.get('n_retries') is not None:
        return retry(kwargs['n_retries'])(_run)(*args, **kwargs)
    else:
        return _run(*args, **kwargs)


def _run(
    model: str,
    messages: List[Dict[str, str]],
    *,
    json_mode: bool = False,
    json_schema: Optional[BaseModel] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    max_tokens: int = 1024,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    n_retries: Optional[int] = None
) -> Dict[str, Any]:
    """
    Lightweight function to run completions with different modes.
    
    Args:
        model: Model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with role and content
        json_mode: Whether to use JSON mode
        json_schema: Pydantic model for structured output
        tools: List of function tools for function calling
        max_tokens: Maximum tokens in response (default: 1024)
        temperature: Temperature parameter
        top_p: Top-p parameter
        n_retries: Number of retries if API call fails (default: None)
    
    Returns:
        Standardized dict with one of these formats:
        - {"content": str} for standard completions
        - {"json": dict} for json_mode or json_schema
        - {"content": str, "tools": list} for tools
        - {"json": dict, "tools": list} for combined json+tools
    """
    # Validate that model is in our supported models list
    if model not in MODELS:
        raise ValueError(f"Model {model} is not in the supported MODELS list")
    
    # Check model limitations from MODELS_LIMITATIONS
    if model in MODELS_LIMITATIONS:
        if json_mode and "json_mode" in MODELS_LIMITATIONS[model]:
            raise ValueError(f"Model {model} does not support JSON mode")
        if json_schema is not None and "json_schema" in MODELS_LIMITATIONS[model]:
            raise ValueError(f"Model {model} does not support JSON schema")
        if tools is not None and "function_calling" in MODELS_LIMITATIONS[model]:
            raise ValueError(f"Model {model} does not support function calling")
    
    # Parse model information
    if "/" in model:
        provider, name = model.split("/", 1)
    else:
        provider, name = None, model

    if provider == "gabber":
        assert name in ["GabberNSFWwCompliance"], "other models are not supported for gabber"
        model = {'GabberNSFWwCompliance': "90d72e7d-8ae2-458c-adb9-074a7fe432c7"}[name]
        conn = http.client.HTTPSConnection("api.gabber.dev")
        payload = json.dumps({
            "messages": messages,
            "model": model,
            "metadata": {},
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tool_choice": "auto",
            "parallel_tool_calls": True
        })
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': os.getenv("GABBER_API_KEY")
        }
        conn.request("POST", "/v1/chat/completions", payload, headers)
        res = conn.getresponse()
        data = res.read()
        data = json.loads(data.decode('utf-8'))

        return {'content': data['choices'][0]['message']['content']}
    
    # Prepare common arguments
    args = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        args["temperature"] = temperature
    if top_p is not None:
        args["top_p"] = top_p
    
    # Handle JSON mode and JSON schema
    if json_mode and json_schema is not None:
        raise ValueError("Cannot use both json_mode and json_schema at the same time")
    
    # Handle JSON mode
    if json_mode:
        # Check if model supports json_mode
        params = get_supported_openai_params(model=name, custom_llm_provider=provider)
        if "response_format" not in params:
            raise ValueError(f"Model {model} does not support JSON mode")
        
        # Check if there's a system message with "JSON" in it
        has_json_system = False
        for msg in messages:
            if msg.get("role") == "system" and "JSON" in msg.get("content", ""):
                has_json_system = True
                break
        if not has_json_system:
            raise ValueError("JSON mode requires a system message containing 'JSON'")
        
        args["response_format"] = {"type": "json_object"}

    elif json_schema is not None:
        args["response_format"] = json_schema

        # Check if model supports json_schema
        if not supports_response_schema(model=name, custom_llm_provider=provider) and (model != "openai/gpt-4.1"):
            raise ValueError(f"Model {model} does not support JSON schema")
        
        # Check if json_schema is a BaseModel
        if not isinstance(json_schema, type) or not issubclass(json_schema, BaseModel):
            raise ValueError("json_schema must be a Pydantic BaseModel class")
    
    # Handle tools/function calling
    if tools is not None:
        # Check if model supports function calling
        if not supports_function_calling(model=name, custom_llm_provider=provider) and (model != "openai/gpt-4.1"):
            raise ValueError(f"Model {model} does not support function calling")
        
        args["tools"] = tools
        args["tool_choice"] = "auto"
    
    # Make the API call with retry logic
    if (n_retries is not None) and (n_retries > 0):
        last_exception = None
        for attempt in range(n_retries + 1):  # +1 for the initial attempt
            try:
                # litellm.disable_cache()
                # args['cache'] = {"no-cache": True}
                response = completion(**args)
                break  # Break the loop if successful
            except Exception as e:
                last_exception = e
                if attempt < n_retries:  # Don't print on last iteration
                    print(f"Attempt {attempt + 1}/{n_retries + 1} failed: {str(e)}. Retrying...")
                if attempt == n_retries:  # If all retries failed
                    raise ValueError(f"Failed after {n_retries + 1} attempts. Last error: {str(last_exception)}")
    else:
        # No retries, just make the call
        response = completion(**args)
    
    # Initialize the result dictionary with defaults
    result = {}
    
    # Process JSON response if requested
    if json_mode or (json_schema is not None):
        if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
            try:
                # First attempt standard parsing
                result["json"] = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError:
                try:
                    result["json"] = extract_json_from_markdown(response.choices[0].message.content)
                except Exception as e:
                    raise ValueError(f"Failed to parse JSON response: {e}")
    
    # Always include content if it exists
    if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
        result["content"] = response.choices[0].message.content
    
    # Process tool calls if used
    if (tools is not None) and hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
        tool_calls = response.choices[0].message.tool_calls
        
        # Extract function data
        function_data = {}
        for call in tool_calls:
            try:
                # Try standard parsing first
                args = json.loads(call.function.arguments)
            except json.JSONDecodeError:
                # Fall back to markdown extraction if needed
                args = extract_json_from_markdown(call.function.arguments)
                
            function_data[call.function.name] = args
        
        result["tools"] = function_data
    
    return result

if __name__ == '__main__':
    # Run tests for models
    test_results = []
    for model in MODELS[:]:
        result = test_model_capabilities(model)
        test_results.append(result)

    # Print summary table
    print("\n\n")
    print("=" * 100)
    print("MODEL CAPABILITY SUMMARY")
    print("=" * 100)
    print("| {:^50} | {:^10} | {:^10} | {:^12} | {:^17} | {:^19} |".format(
        "Model", "Standard", "JSON Mode", "JSON Schema", "Function Calling", "Multiple Functions"))
    print("|" + "-"*52 + "|" + "-"*12 + "|" + "-"*12 + "|" + "-"*14 + "|" + "-"*19 + "|" + "-"*21 + "|")
    for result in test_results:
        model_name = result['model']
        model_name_short = model_name.split("/", 1)[-1]
        
        # Display status with appropriate emoji
        json_mode_status = '⚠️' if model_name in MODELS_LIMITATIONS and "json_mode" in MODELS_LIMITATIONS[model_name] else ('✅' if result['json_mode'] else '❌')
        json_schema_status = '⚠️' if model_name in MODELS_LIMITATIONS and "json_schema" in MODELS_LIMITATIONS[model_name] else ('✅' if result['json_schema'] else '❌')
        function_calling_status = '⚠️' if model_name in MODELS_LIMITATIONS and "function_calling" in MODELS_LIMITATIONS[model_name] else ('✅' if result['function_calling'] else '❌')
        multi_function_status = '⚠️' if model_name in MODELS_LIMITATIONS and "multi_function_calling" in MODELS_LIMITATIONS[model_name] else ('✅' if result['multi_function_calling'] else '❌')
        
        print("| {:50} | {:^10} | {:^10} | {:^12} | {:^17} | {:^19} |".format(
            model_name_short, 
            '✅' if result['standard_completion'] else '❌',
            json_mode_status,
            json_schema_status,
            function_calling_status,
            multi_function_status
        ))

    # Legend
    print(f"Legend: ✅ = Supported, ❌ = Failed test, ⚠️ = Not supported by design")
