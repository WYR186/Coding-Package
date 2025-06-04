# test_app_no_apikey.py

import os
import unittest
from unittest.mock import patch, MagicMock

import llm_toolkit as app  # assumes llm_toolkit_py is in the same directory


# ─────────── Dummy Response Classes ───────────

class DummyUsage:
    def __init__(self, p=1, c=2):
        self.prompt_tokens = p
        self.completion_tokens = c
        self.total_tokens = p + c

class DummyResponseChat:
    def __init__(self, content: str):
        msg = MagicMock()
        msg.content = content
        ch = MagicMock()
        ch.message = msg
        self.choices = [ch]
        self.usage = DummyUsage(3, 5)

class DummyResponseCompletion:
    def __init__(self, text: str):
        ch = MagicMock()
        ch.text = text
        self.choices = [ch]
        self.usage = DummyUsage(4, 6)


# ─────────── Dummy Clients ───────────

class FakeOpenAIClient:
    def __init__(self):
        self.chat = MagicMock()
        self.completions = MagicMock()
        self.chat.completions.create = MagicMock(
            return_value=DummyResponseChat("OPENAI_CHAT")
        )
        self.completions.create = MagicMock(
            return_value=DummyResponseCompletion("OPENAI_COMP")
        )

class FakeAnthropicClient:
    def __init__(self):
        self.messages = MagicMock()
        resp = MagicMock()
        resp.content = [MagicMock()]
        resp.content[0].text = "ANTHRO_CHAT"
        resp.usage = MagicMock()
        resp.usage.input_tokens = 7
        resp.usage.output_tokens = 11
        self.messages.create = MagicMock(return_value=resp)

class FakeDeepSeekClient:
    def __init__(self):
        self.chat = MagicMock()
        self.completions = MagicMock()
        self.chat.completions.create = MagicMock(
            return_value=DummyResponseChat("DEEPCHAT")
        )
        self.completions.create = MagicMock(
            return_value=DummyResponseCompletion("DEEPCOMP")
        )


# ─────────── Test Case ───────────

class TestAppNoApiKeyMgmt(unittest.TestCase):
    def setUp(self):
        # Backup real clients
        self.orig_openai_client = app.openai_client
        self.orig_anth_client = app.anth_client
        self.orig_deepseek_client = app.deepseek_client

        # Inject fakes
        app.openai_client = FakeOpenAIClient()
        app.anth_client = FakeAnthropicClient()
        app.deepseek_client = FakeDeepSeekClient()

        # Create sample text files
        os.makedirs("To_Summarize", exist_ok=True)
        with open("To_Summarize/test_doc.txt", "w", encoding="utf-8") as f:
            f.write("This is a test document for summarizer.")
        with open("To_Summarize/test_lecture.txt", "w", encoding="utf-8") as f:
            f.write("Lecture transcript line A.\nLecture transcript line B.")

    def tearDown(self):
        # Restore original clients
        app.openai_client = self.orig_openai_client
        app.anth_client = self.orig_anth_client
        app.deepseek_client = self.orig_deepseek_client

        # Clean up files
        try:
            os.remove("To_Summarize/test_doc.txt")
            os.remove("To_Summarize/test_lecture.txt")
        except:
            pass

    def test_summarize_text_openai_chat(self):
        summary, usage = app.summarize_text("openai", "gpt-3.5-turbo", "Dummy")
        self.assertEqual(summary, "OPENAI_CHAT")
        self.assertEqual(usage["prompt_tokens"], 3)
        self.assertEqual(usage["completion_tokens"], 5)

    def test_summarize_text_openai_completion(self):
        summary, usage = app.summarize_text("openai", "o1-mini", "Dummy")
        self.assertEqual(summary, "OPENAI_COMP")
        self.assertEqual(usage["prompt_tokens"], 4)
        self.assertEqual(usage["completion_tokens"], 6)

    def test_summarize_text_anthropic(self):
        summary, usage = app.summarize_text("anthropic", "claude-3-5-sonnet-20241022", "Text")
        self.assertEqual(summary, "ANTHRO_CHAT")
        self.assertEqual(usage["prompt_tokens"], 7)
        self.assertEqual(usage["completion_tokens"], 11)

    def test_summarize_text_deepseek_chat(self):
        summary, usage = app.summarize_text("deepseek", "deepseek-chat", "Text")
        self.assertEqual(summary, "DEEPCHAT")
        self.assertEqual(usage["prompt_tokens"], 3)
        self.assertEqual(usage["completion_tokens"], 5)

    def test_summarize_text_deepseek_completion(self):
        summary, usage = app.summarize_text("deepseek", "other-model", "Text")
        self.assertEqual(summary, "DEEPCOMP")
        self.assertEqual(usage["prompt_tokens"], 4)
        self.assertEqual(usage["completion_tokens"], 6)

    def test_lecture_summarize_openai_english(self):
        out, usage = app.lecture_summarize("openai", "gpt-4", "To_Summarize/test_lecture.txt", "en")
        self.assertIn("OPENAI_CHAT", out)
        self.assertEqual(usage["prompt_tokens"], 3)
        self.assertEqual(usage["completion_tokens"], 5)

    def test_lecture_summarize_openai_chinese(self):
        out, usage = app.lecture_summarize("openai", "gpt-4", "To_Summarize/test_lecture.txt", "cn")
        self.assertIn("OPENAI_CHAT", out)

    def test_lecture_summarize_anthropic(self):
        out, usage = app.lecture_summarize("anthropic", "claude-3-5-sonnet-20241022", "To_Summarize/test_lecture.txt", "en")
        self.assertIn("ANTHRO_CHAT", out)
        self.assertEqual(usage["prompt_tokens"], 7)
        self.assertEqual(usage["completion_tokens"], 11)

    def test_lecture_summarize_deepseek(self):
        out, usage = app.lecture_summarize("deepseek", "deepseek-reasoner", "To_Summarize/test_lecture.txt", "en")
        self.assertIn("DEEPCHAT", out)
        self.assertEqual(usage["prompt_tokens"], 3)
        self.assertEqual(usage["completion_tokens"], 5)

    def test_chat_openai(self):
        with patch("builtins.input", side_effect=["Hello OpenAI", ""]):
            ok = app.chat_once("openai", "gpt-3.5-turbo")
            self.assertTrue(ok)

    def test_chat_anthropic(self):
        with patch("builtins.input", side_effect=["Hello Anthropic", ""]):
            ok = app.chat_once("anthropic", "claude-3-5-sonnet-20241022")
            self.assertTrue(ok)

    def test_chat_deepseek(self):
        with patch("builtins.input", side_effect=["Hello Deepseek", ""]):
            ok = app.chat_once("deepseek", "deepseek-chat")
            self.assertTrue(ok)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAppNoApiKeyMgmt)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        print("\nAll tests passed successfully.")
    else:
        print("\nSome tests failed. See details above.")
