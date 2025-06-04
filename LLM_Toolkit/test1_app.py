import os
import tempfile
import llm_toolkit as app  # assumes llm_toolkit_py is in the same directory
from llm_toolkit import (
    list_openai_models,
    list_anthropic_models,
    list_deepseek_models,
    chat_once,
    summarize_text,
    lecture_summarize
)

def test_chat(provider, model):
    print(f"\nTesting CHAT for {provider} - {model}")
    try:
        # 模拟用户输入：“Hello what model are you? ” 然后空行退出
        from unittest.mock import patch
        inputs = ["Hello test chat", ""]  # 第二个空字符串导致 chat_once() 返回 False 退出
        with patch('builtins.input', side_effect=inputs):
            success = chat_once(provider, model)
        if success:
            print("  CHAT: Success")
        else:
            print("  CHAT: Returned False (likely because input ended)")
    except Exception as e:
        print(f"  CHAT: Exception -> {e}")

def test_summarizer(provider, model):
    print(f"\nTesting SUMMARY for {provider} - {model}")
    try:
        text = "This is a test text for summarization."
        summary, usage = summarize_text(provider, model, text)
        if summary:
            print(f"  SUMMARY: Success, got summary: {summary[:50]}... | Usage: {usage}")
        else:
            print("  SUMMARY: Returned None or empty")
    except Exception as e:
        print(f"  SUMMARY: Exception -> {e}")

def test_lecture(provider, model):
    print(f"\nTesting LECTURE for {provider} - {model}")
    try:
        # 创建临时文件，写入几行测试文本
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.txt') as tmp:
            tmp.write("This is a test lecture content.\nIt has multiple lines.\nEnd.")
            tmp_path = tmp.name

        lecture, usage = lecture_summarize(provider, model, tmp_path, "en")
        os.unlink(tmp_path)
        if lecture:
            print(f"  LECTURE: Success, output length = {len(lecture)} characters | Usage: {usage}")
        else:
            print("  LECTURE: Returned None or empty")
    except Exception as e:
        print(f"  LECTURE: Exception -> {e}")

def main():
    print("=== MODEL AVAILABILITY TEST ===")

    # OpenAI
    openai_models = list_openai_models()
    print("\nOpenAI models detected:")
    for m in openai_models:
        print(f" - {m}")

    # Anthropic
    anth_models = list_anthropic_models()
    print("\nAnthropic models detected:")
    for m in anth_models:
        print(f" - {m}")

    # DeepSeek
    ds_models = list_deepseek_models()
    print("\nDeepSeek models detected:")
    for m in ds_models:
        print(f" - {m}")

    # 对每个 OpenAI 模型依次运行三项测试
    for m in openai_models:
        test_chat("openai", m)
        test_summarizer("openai", m)
        test_lecture("openai", m)

    # 对每个 Anthropic 模型依次运行三项测试
    for m in anth_models:
        test_chat("anthropic", m)
        test_summarizer("anthropic", m)
        test_lecture("anthropic", m)

    # 对每个 DeepSeek 模型依次运行三项测试
    for m in ds_models:
        test_chat("deepseek", m)
        test_summarizer("deepseek", m)
        test_lecture("deepseek", m)

if __name__ == "__main__":
    main()
