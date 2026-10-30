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

def get_embedding(text, model="qwen2.5:1.5b"):
    """
    テキストの埋め込みベクトルを取得します。
    OllamaのOpenAI互換APIを呼び出し、失敗した場合はダミーベクトル(1536次元)を返します。
    """
    text = str(text).replace("\n", " ")
    if not text.strip():
        text = "empty"
    try:
        response = client.embeddings.create(
            input=[text],
            model=model
        )
        return response.data[0].embedding
    except Exception:
        return [0.0] * 1536

import os

def generate_prompt(prompt_input, prompt_template):
    """
    プロンプトテンプレート(txtファイル)の変数を入力値で置換し、
    LLMに渡すテキストを生成します。
    """
    if isinstance(prompt_input, str):
        prompt_input = [prompt_input]
    
    # 相対パスで見つからない場合、backend_server ディレクトリ基準で補正
    if not os.path.exists(prompt_template):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        alt_path = os.path.join(base_dir, prompt_template)
        if os.path.exists(alt_path):
            prompt_template = alt_path

    with open(prompt_template, "r", encoding="utf-8") as f:
        prompt = f.read()
        
    for count, i in enumerate(prompt_input):
        prompt = prompt.replace(f"!<INPUT {count}>!", str(i))
        
    if "<!__func_clean_up__!>" in prompt:
        prompt = prompt.split("<!__func_clean_up__!>")[0]
        
    return prompt

def GPT_request(prompt, model="qwen2.5:1.5b"):
    """
    Ollama (OpenAI 互換 API) へプロンプトを送信し、テキスト応答を取得します。
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        print(f"LLM API Call Error: {e}")
        return ""

def safe_generate_response(prompt,
                           gpt_parameter=None,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False):
    """
    LLMに応答を要求し、バリデーションとクリーンアップを行って安全に結果を返します。
    失敗した場合は指定回数リトライし、最終的に fail_safe_response を返します。
    """
    if verbose:
        print("--- PROMPT ---")
        print(prompt)

    for i in range(repeat):
        try:
            curr_gpt_response = GPT_request(prompt)

            if func_clean_up:
                cleaned_response = func_clean_up(curr_gpt_response, prompt)
            else:
                cleaned_response = curr_gpt_response

            if func_validate:
                if func_validate(curr_gpt_response, prompt):
                    return cleaned_response
            else:
                return cleaned_response

        except Exception as e:
            if verbose:
                print(f"Attempt {i+1} failed: {e}")

    return fail_safe_response

# エイリアス設定
ChatGPT_safe_generate_response = safe_generate_response
