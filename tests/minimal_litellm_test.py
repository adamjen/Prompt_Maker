import litellm
import os

# Enable LiteLLM debugging for detailed output
litellm._turn_on_debug()

api_base = os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234/v1")
api_key = "sk-test"  # Dummy key required by LiteLLM
model_name = os.getenv("LMSTUDIO_MODEL_NAME", "qwen3-1.7b")
litellm_model_name = f"openai/{model_name}"

print(f"Attempting to connect to LM Studio at: {api_base}")
print(f"Attempting LiteLLM completion with model: {litellm_model_name}")

try:
    response = litellm.completion(
        model=litellm_model_name,
        messages=[{"role": "user", "content": "Hello, what is the capital of France?"}],
        temperature=0.7,
        api_base=api_base,
        api_key=api_key
    )

    print("\nLiteLLM completion successful!")
    print("Response:")
    print(response)

except Exception as e:
    print(f"\nAn error occurred during LiteLLM completion: {type(e).__name__}: {e}")
    print("Please ensure LM Studio is running and the API server is accessible on the specified port.")