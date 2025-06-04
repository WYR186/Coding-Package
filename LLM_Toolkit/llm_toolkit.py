import os
import json
import textwrap

# ———————— 1. Load and Persist API Keys ————————
KEYS_FILE = "api_keys.json"

def load_api_keys():
    """
    Load existing API keys from KEYS_FILE if present; otherwise return (None, None, None).
    """
    if os.path.isfile(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return (
                    data.get("OPENAI_API_KEY"),
                    data.get("ANTHROPIC_API_KEY"),
                    data.get("DEEPSEEK_API_KEY")
                )
        except Exception:
            return (None, None, None)
    return (None, None, None)

def save_api_keys(openai_key, anthropic_key, deepseek_key):
    """
    Persist provided API keys to KEYS_FILE.
    """
    try:
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "OPENAI_API_KEY": openai_key,
                "ANTHROPIC_API_KEY": anthropic_key,
                "DEEPSEEK_API_KEY": deepseek_key
            }, f, indent=2, ensure_ascii=False)
        print(f"Saved API keys to {KEYS_FILE}.")
    except Exception as e:
        print(f"⚠️ Could not write to {KEYS_FILE}: {e}")

def configure_api_keys(existing_openai, existing_anthropic, existing_deepseek):
    """
    Allow user to individually add/update API keys for OpenAI, Anthropic, or DeepSeek.
    Returns a tuple (openai_key, anthropic_key, deepseek_key).
    """
    openai_key = existing_openai
    anthropic_key = existing_anthropic
    deepseek_key = existing_deepseek
    updated = False

    while True:
        print("\n=== Configure API Keys ===")
        print(f"1. OpenAI key [{'Present' if openai_key else 'Missing'}]")
        print(f"2. Anthropic key [{'Present' if anthropic_key else 'Missing'}]")
        print(f"3. DeepSeek key [{'Present' if deepseek_key else 'Missing'}]")
        print("0. Return to main menu")
        choice = input("Select provider to add/update (0–3): ").strip()

        if choice == "0":
            break

        if choice == "1":
            # OpenAI
            if openai_key:
                print("OpenAI key is currently present.")
                sub = input("Update OpenAI key? (y/n): ").strip().lower()
                if sub == "y":
                    new_key = input("Enter new OpenAI API key (or leave blank to remove): ").strip()
                    openai_key = new_key or None
                    updated = True
            else:
                new_key = input("Enter your OpenAI API key (required to set): ").strip()
                if new_key:
                    openai_key = new_key
                    updated = True
                else:
                    print("OpenAI key cannot be empty if you wish to set it.")
        elif choice == "2":
            # Anthropic
            if anthropic_key:
                print("Anthropic key is currently present.")
                sub = input("Update Anthropic key? (y/n): ").strip().lower()
                if sub == "y":
                    new_key = input("Enter new Anthropic API key (or leave blank to remove): ").strip()
                    anthropic_key = new_key or None
                    updated = True
            else:
                new_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
                if new_key:
                    anthropic_key = new_key
                    updated = True
        elif choice == "3":
            # DeepSeek
            if deepseek_key:
                print("DeepSeek key is currently present.")
                sub = input("Update DeepSeek key? (y/n): ").strip().lower()
                if sub == "y":
                    new_key = input("Enter new DeepSeek API key (or leave blank to remove): ").strip()
                    deepseek_key = new_key or None
                    updated = True
            else:
                new_key = input("Enter your DeepSeek API key (or press Enter to skip): ").strip()
                if new_key:
                    deepseek_key = new_key
                    updated = True
        else:
            print("Invalid choice, please enter 0, 1, 2, or 3.")

    if updated:
        save_api_keys(openai_key, anthropic_key, deepseek_key)
    else:
        print("No changes to API keys.")

    return openai_key, anthropic_key, deepseek_key

# Load existing keys
openai_api_key, anthropic_api_key, deepseek_api_key = load_api_keys()

# ———————— 2. Initialize Clients ————————
from openai import OpenAI
openai_client = None
anth_client = None
deepseek_client = None

if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)

if anthropic_api_key:
    try:
        from anthropic import Anthropic
        anth_client = Anthropic(api_key=anthropic_api_key)
    except ImportError:
        print("⚠️ Anthropic package not installed. Anthropic models will be unavailable.")
        anth_client = None

# 修复点1: 使用正确的 API 端点（无路径）
if deepseek_api_key:
    deepseek_client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

# ———————— 3. Fetch Available Models per Provider ————————
def list_openai_models():
    """
    Return a predefined list of stable OpenAI 'gpt-' series models.
    """
    return [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4.1-mini"
    ]

def list_anthropic_models():
    """
    Return a list of common Anthropic Claude models.
    """
    if not anth_client:
        return []
    predefined_models = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]
    try:
        resp = anth_client.models.list()
        names = []
        if hasattr(resp, "data") and resp.data:
            for m in resp.data:
                if hasattr(m, "id"):
                    names.append(m.id)
                elif isinstance(m, dict) and "id" in m:
                    names.append(m["id"])
        return names or predefined_models
    except Exception:
        return predefined_models

# 修复点2: 正确获取 DeepSeek 模型列表
def list_deepseek_models():
    """
    Return a list of DeepSeek models.
    """
    if not deepseek_client:
        return []
    try:
        models = deepseek_client.models.list().data
        return [model.id for model in models]
    except Exception as e:
        print(f"Error fetching DeepSeek models: {e}")
        return [
            "deepseek-chat",
            "deepseek-coder",
            "deepseek-math"
        ]

# ———————— 4. Client Selector Based on Provider ————————
def get_client_for_model(provider: str):
    """
    Given provider string "openai", "anthropic", or "deepseek", return the appropriate client.
    """
    if provider == "anthropic":
        if not anth_client:
            print("❌ No Anthropic client available.")
            return None
        return anth_client
    elif provider == "deepseek":
        if not deepseek_client:
            print("❌ No DeepSeek client available.")
            return None
        return deepseek_client
    else:  # "openai"
        if not openai_client:
            print("❌ No OpenAI client available.")
            return None
        return openai_client

# ———————— 5. Chatbot Functionality ————————
def chat_once(provider: str, model: str):
    """
    One round of chat: use appropriate API based on provider.
    Returns False if user input is empty.
    """
    user_input = input("\n[Chat] You: ").strip()
    if not user_input:
        return False

    client = get_client_for_model(provider)
    if not client:
        return False

    print("Thinking...")

    if provider == "anthropic":
        try:
            response = client.messages.create(
                model=model,
                max_tokens=512,
                temperature=0.7,
                messages=[{"role": "user", "content": user_input}]
            )
            assistant_reply = response.content[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
        except Exception as e:
            print(f"Error calling Anthropic Chat API: {e}")
            return False

    # 修复点3: DeepSeek 使用 Chat API
    elif provider == "deepseek" or model.startswith("gpt-"):
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=512,
            )
            assistant_reply = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        except Exception as e:
            print(f"Error calling {provider.capitalize()} Chat API: {e}")
            return False

    else:
        try:
            response = client.completions.create(
                model=model,
                prompt=user_input,
                temperature=0.7,
                max_tokens=512,
            )
            assistant_reply = response.choices[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        except Exception as e:
            print(f"Error calling {provider.capitalize()} Completion API: {e}")
            return False

    print(f"[Chat] Assistant ({provider}):", assistant_reply)
    print(f"[Usage] prompt: {usage['prompt_tokens']}  completion: {usage['completion_tokens']}  total: {usage['total_tokens']}")
    return True

# ———————— 6. File Loading Helper ————————
def load_text_from_file(path: str) -> str | None:
    """
    Read a text file and return its content. Strip surrounding quotes if present.
    Return None on error.
    """
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        return None
    except OSError as e:
        print(f"❌ Unable to open file: {e}")
        return None

# ───────── 7. Text Summarizer (NO extra "Thinking…") ─────────
def summarize_text(provider: str, model: str, text: str,
                   summary_length: str = "within three sentences"):
    """
    Summarize given text with specified provider and model.
    Returns (summary, usage_dict) or (None, None) on error.
    """
    client = get_client_for_model(provider)
    if not client:
        return None, None

    prompt_text = (
        f"Please summarize the following text {summary_length}:\n\n"
        f"{text}\n\n"
        "Output the summary only."
    )

    # one “Thinking…” is printed by caller
    if provider == "anthropic":
        try:
            response = client.messages.create(
                model=model,
                max_tokens=256,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt_text}]
            )
            summary = response.content[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            return summary, usage
        except Exception as e:
            print(f"Error calling Anthropic Summarizer API: {e}")
            return None, None

    # 修复点4: 仅对话模型使用 Chat API
    elif provider == "deepseek" and "chat" in model.lower():
        messages = [
            {"role": "system", "content": "You are a summarization expert."},
            {"role": "user", "content": prompt_text},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=256,
            )
            summary = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return summary, usage
        except Exception as e:
            print(f"Error calling DeepSeek Summarizer (Chat) API: {e}")
            return None, None

    # 修复点5: 非对话模型使用 Completion API
    elif provider == "deepseek":
        try:
            response = client.completions.create(
                model=model,
                prompt=prompt_text,
                temperature=0.3,
                max_tokens=256,
            )
            summary = response.choices[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return summary, usage
        except Exception as e:
            print(f"Error calling DeepSeek Summarizer (Completion) API: {e}")
            return None, None

    # 修复点6: OpenAI 模型保持原逻辑
    elif model.startswith("gpt-"):
        messages = [
            {"role": "system", "content": "You are a summarization expert."},
            {"role": "user", "content": prompt_text},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=256,
            )
            summary = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return summary, usage
        except Exception as e:
            print(f"Error calling OpenAI Summarizer API: {e}")
            return None, None

    else:
        try:
            response = client.completions.create(
                model=model,
                prompt=prompt_text,
                temperature=0.3,
                max_tokens=256,
            )
            summary = response.choices[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return summary, usage
        except Exception as e:
            print(f"Error calling {provider.capitalize()} Summarizer (completion) API: {e}")
            return None, None


# ———————— 8. Lecture Summarizer Functionality ————————
def lecture_summarize(provider: str, model: str, path: str, language: str):
    """
    Read a lecture transcript and generate a detailed explanation.
    provider: "openai", "anthropic", or "deepseek"
    language: "en" for English only, "cn" for Chinese with English keywords.
    Returns (lecture_summary, usage_dict) or (None, None).
    """
    transcript = load_text_from_file(path)
    if transcript is None:
        return None, None

    # Build prompt differently depending on language
    if language == "en":
        # English-only template
        prompt_template = f"""
Answer in English only. Do not omit any lecture transcript details.
Your task: refer only to the provided lecture transcript (including audio transcript),
and combine all details the instructor said during class. Provide a complete,
systematic, in-depth explanation. This session focuses on the lecture transcript.
If the transcript includes code examples, formula derivations, or Q&A interactions,
explain each item one by one in English. Highlight which concepts are most important
and likely exam topics, and explain why. List any exam points the instructor mentioned
("Will be on exam"/"Won't be on exam").
If none are mentioned, state "Instructor did not explicitly specify exam points," and
suggest likely exam topics. Provide five English concept questions at the end, then
answers and give detailed explanations.

Lecture transcript below:
{transcript}
"""
    else:
        # Chinese-with-English-keywords template
        prompt_template = f"""
Answer in Chinese and include English keywords. Do not omit any lecture transcript details.
您的任务：只参考提供的课程转录（包括录音转写内容），结合老师上课的所有细节，给出完整、
系统、深入的讲解。本节课主要聚焦 Lecture 转录内容。如果转录中出现示例代码、公式推导
或课堂互动中的提问与回答，请逐条解释。对于每个概念或算法，先给出中文解释，再列出核心
英文关键词。标出哪些概念最重要、最容易在考试中出现并解释原因。列出老师在录音中提到的
"Will be on exam"/"Won't be on exam"的英文原话并在括号中给出中文翻译。如果没有明确提及，
请说明"Instructor did not explicitly specify exam points"，并结合转录内容总结可能考点。最后
用英文出五道概念题，并在末尾给出中文详细解析。

Lecture transcript below:
{transcript}
"""

    client = get_client_for_model(provider)
    if not client:
        return None, None

    print("Thinking...")

    if provider == "anthropic":
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt_template}]
            )
            lecture_summary = response.content[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
            return lecture_summary, usage
        except Exception as e:
            print(f"Error calling Anthropic Lecture Summarizer API: {e}")
            return None, None

    # 修复点7: DeepSeek 使用 Chat API
    elif provider == "deepseek" or model.startswith("gpt-"):
        messages = [
            {"role": "system", "content": "You are a professional university course explanation assistant."},
            {"role": "user",   "content": prompt_template},
        ]
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
            )
            lecture_summary = response.choices[0].message.content.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return lecture_summary, usage
        except Exception as e:
            print(f"Error calling {provider.capitalize()} Lecture Summarizer API: {e}")
            return None, None

    else:
        try:
            response = client.completions.create(
                model=model,
                prompt=prompt_template,
                temperature=0.3,
                max_tokens=2048,
            )
            lecture_summary = response.choices[0].text.strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            return lecture_summary, usage
        except Exception as e:
            print(f"Error calling {provider.capitalize()} Lecture Summarizer (completion) API: {e}")
            return None, None

# ———————— 9. Main Menu and Control Flow ————————
def main():
    global openai_api_key, anthropic_api_key, deepseek_api_key, openai_client, anth_client, deepseek_client

    while True:
        print("\n======== LLM Toolkit ========")
        print("1. Chatbox")
        print("2. Text Summarizer")
        print("3. Lecture Summarizer")
        print("4. Manage API Keys")
        print("0. Exit")
        choice = input("Enter 0/1/2/3/4 and press Enter: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        if choice == "4":
            openai_api_key, anthropic_api_key, deepseek_api_key = configure_api_keys(
                openai_api_key, anthropic_api_key, deepseek_api_key
            )
            openai_client = OpenAI(api_key=openai_api_key)
            if anthropic_api_key:
                try:
                    from anthropic import Anthropic
                    anth_client = Anthropic(api_key=anthropic_api_key)
                except ImportError:
                    print("⚠️ Anthropic package not installed. Anthropic models will be unavailable.")
                    anth_client = None
            else:
                anth_client = None

            # 修复点8: 使用正确的 API 端点（无路径）
            if deepseek_api_key:
                deepseek_client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
            else:
                deepseek_client = None

            continue

        if choice in ["1", "2", "3"]:
            if not openai_api_key:
                print("❌ OpenAI API key is required. Please manage API keys first.")
                continue

        print("\nSelect provider:")
        print("1. OpenAI")
        print("2. Anthropic")
        print("3. DeepSeek")
        print("0. Cancel")
        provider_choice = input("Enter 0/1/2/3: ").strip()
        if provider_choice == "0":
            continue
        elif provider_choice == "1":
            provider = "openai"
            model_list = list_openai_models()
        elif provider_choice == "2":
            provider = "anthropic"
            if not anthropic_api_key:
                print("❌ Anthropic key not configured. Choose another provider or manage keys.")
                continue
            model_list = list_anthropic_models()
        elif provider_choice == "3":
            provider = "deepseek"
            if not deepseek_api_key:
                print("❌ DeepSeek key not configured. Choose another provider or manage keys.")
                continue
            model_list = list_deepseek_models()
        else:
            print("Invalid provider choice.")
            continue

        if not model_list:
            print(f"❌ No models available for {provider.capitalize()}.")
            continue

        print(f"\nAvailable {provider.capitalize()} models:")
        for idx, name in enumerate(model_list, 1):
            print(f"{idx}. {name}")
        print("0. Cancel")
        sel = input(f"Enter model number (1–{len(model_list)}), or 0 to cancel: ").strip()
        try:
            sel_idx = int(sel) - 1
            if sel == "0":
                continue
            if not (0 <= sel_idx < len(model_list)):
                print("Invalid model selection.")
                continue
            model_name = model_list[sel_idx]
        except ValueError:
            print("Invalid input.")
            continue

        if choice == "1":
            print("\n>>> Entering Chatbox mode. Press Enter on an empty line to return to main menu.")
            while True:
                cont = chat_once(provider, model_name)
                if not cont:
                    print(">>> Exiting Chatbox, returning to main menu.\n")
                    break

        elif choice == "2":
            print("\n>>> Entering Text Summarizer mode.")
            to_summarize_dir = os.path.join(os.getcwd(), "To_Summarize")
            if not os.path.isdir(to_summarize_dir):
                print(f"❌ Folder not found: {to_summarize_dir}")
                print("Please create 'To_Summarize' and put .txt files there.\n")
                continue

            files = [f for f in os.listdir(to_summarize_dir) if os.path.isfile(os.path.join(to_summarize_dir, f))]
            if not files:
                print(f"❌ No files in folder: {to_summarize_dir}")
                print("Please add .txt files to 'To_Summarize'.\n")
                continue

            print("\nFiles available for summarization:")
            for i, fname in enumerate(files, 1):
                print(f"{i}. {fname}")
            print(f"{len(files) + 1}. [Enter custom path]")

            sel_file = input(f"\nEnter number (1–{len(files)}) to select file, or {len(files)+1} for custom path: ").strip()
            try:
                idx_file = int(sel_file) - 1
                if sel_file == str(len(files) + 1):
                    file_path = input("Enter full path to the .txt file: ").strip()
                    if not file_path:
                        print("Empty path, returning to main menu.\n")
                        continue
                elif 0 <= idx_file < len(files):
                    file_path = os.path.join(to_summarize_dir, files[idx_file])
                else:
                    print("Invalid selection, returning to main menu.\n")
                    continue
            except ValueError:
                print("Invalid input, returning to main menu.\n")
                continue

            text_content = load_text_from_file(file_path)
            if not text_content:
                print("Failed to read file, returning to main menu.\n")
                continue

            snippet = textwrap.shorten(text_content, width=2000, placeholder="...")
            print("Generating summary. Please wait...")
            # Only one “Thinking…” here
            summary, usage = summarize_text(provider, model_name, snippet)
            if not summary:
                print("Summary generation failed, returning to main menu.\n")
                continue

            print("\n=== Summary Result ===")
            print(summary)
            print("\n=== Token Usage ===")
            print(f"prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']}, total: {usage['total_tokens']}\n")

        elif choice == "3":
            print("\n>>> Entering Lecture Summarizer mode.")
            to_summarize_dir = os.path.join(os.getcwd(), "To_Summarize")
            if not os.path.isdir(to_summarize_dir):
                print(f"❌ Folder not found: {to_summarize_dir}")
                print("Please create 'To_Summarize' and put lecture transcript .txt files there.\n")
                continue

            files = [f for f in os.listdir(to_summarize_dir) if os.path.isfile(os.path.join(to_summarize_dir, f))]
            if not files:
                print(f"❌ No files in folder: {to_summarize_dir}")
                print("Please add lecture transcript .txt files to 'To_Summarize'.\n")
                continue

            print("\nLecture transcript files:")
            for i, fname in enumerate(files, 1):
                print(f"{i}. {fname}")
            print(f"{len(files) + 1}. [Enter custom path]")

            sel_file = input(f"\nEnter number (1–{len(files)}) to select file, or {len(files)+1} for custom path: ").strip()
            try:
                idx_file = int(sel_file) - 1
                if sel_file == str(len(files) + 1):
                    transcript_path = input("Enter full path to the lecture transcript .txt: ").strip()
                    if not transcript_path:
                        print("Empty path, returning to main menu.\n")
                        continue
                elif 0 <= idx_file < len(files):
                    transcript_path = os.path.join(to_summarize_dir, files[idx_file])
                else:
                    print("Invalid selection, returning to main menu.\n")
                    continue
            except ValueError:
                print("Invalid input, returning to main menu.\n")
                continue

            print("Choose response format:")
            print("1. English only")
            print("2. Chinese with English keywords")
            lang_choice = input("Enter 1 or 2 (default 2): ").strip()
            response_language = "en" if lang_choice == "1" else "cn"

            print("Generating lecture summary. Please wait...")
            # Only one “Thinking…” inside lecture_summarize
            lecture_output, lecture_usage = lecture_summarize(
                provider, model_name, transcript_path, response_language
            )
            if not lecture_output:
                print("Lecture summarization failed, returning to main menu.\n")
                continue

            print("\n=== Lecture Summarization Result ===")
            print(lecture_output)
            print("\n=== Token Usage ===")
            print(f"prompt: {lecture_usage['prompt_tokens']}, completion: {lecture_usage['completion_tokens']}, total: {lecture_usage['total_tokens']}\n")

        else:
            print("Invalid choice. Please enter 0, 1, 2, 3, or 4.\n")

if __name__ == "__main__":
    main()
