import os
import requests

COLAB_ENDPOINT = os.getenv("COLAB_ENDPOINT")
COLAB_API_KEY = os.getenv("COLAB_API_KEY")

def call_llm(prompt: str) -> str:
    response = requests.post(
        f"{COLAB_ENDPOINT}/generate",
        headers={"x-api-key": COLAB_API_KEY},
        string={"prompt": prompt},
        timeout=60
    )
    response.raise_for_status()
    return response.text()["generated_text"]
