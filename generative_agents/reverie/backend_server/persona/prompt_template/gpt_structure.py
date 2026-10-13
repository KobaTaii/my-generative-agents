import os
import time
from openai import OpenAI

# Dockerコンテナ間通信（ollama）またはホストのOllama設定
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434/v1")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3.5:3b-instruct")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"  # ダミーAPIキー
)

def temp_sleep(seconds=0.1):
    time.sleep(seconds)

def ChatGPT_request(prompt, model=MODEL_NAME):
    """OpenAI APIへの呼び出しをローカルOllamaに置換"""
    try:
        strict_prompt = prompt + "\n\nRespond strictly in the requested format without any extra markdown wrapper or text."
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": strict_prompt}],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"ローカルLLMエラー: {e}")
        return ""

def GPT4_request(prompt, model=MODEL_NAME):
    return ChatGPT_request(prompt, model)

def GPT_request(prompt, model=MODEL_NAME):
    return ChatGPT_request(prompt, model)
