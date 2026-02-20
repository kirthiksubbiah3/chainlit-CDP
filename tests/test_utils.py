import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock, AsyncMock
import logging
import os
import tempfile
import yaml
from langchain_core.messages import ToolMessage
from git import GitCommandError

import chainlit as cl
import shutil


from src.utils.summarizer import (
    is_text_file,
    read_txt_file,
    read_docx_file,
    read_pdf_file,
    read_attachment,
    MAX_INPUT_CHARS,
)


from src.utils import (
    generate_chat_title_from_input,
    get_log_level,
    get_logger,
    safe_float,
    load_yaml_file,
    merge_dict,
    get_time_taken_message,
    get_username,
    _custom_msgpack_default,
    CleanXMLTagParser,
    get_collection_name,
    get_usage_cost_details,
    send_usage_cost_message,
    log_usage_details,
    log_and_show_usage_details,
    load_chat_profiles,
)

import src.utils.git as git_utils


# config.py
class TestConfigUtils(unittest.TestCase):
    """Unit tests for configuration utility functions (safe_float, load_yaml_file, merge_dict)."""

    # Tests for safe_float
    def test_safe_float_valid(self):
        self.assertEqual(safe_float("3.14"), 3.14)
        self.assertEqual(safe_float(10), 10.0)

    def test_safe_float_invalid_string(self):
        self.assertEqual(safe_float("abc", default=1.23), 1.23)

    def test_safe_float_none(self):
        self.assertEqual(safe_float(None, default=-1.0), -1.0)

    # Tests for load_yaml_file
    def test_load_yaml_file_valid(self):
        data = {"name": "test", "value": 42}
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            yaml.dump(data, tmp)
            tmp_path = tmp.name

        try:
            loaded = load_yaml_file(tmp_path)
            self.assertEqual(loaded, data)
        finally:
            os.remove(tmp_path)

    def test_load_yaml_file_empty(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp:
            tmp.write("")  # empty file
            tmp_path = tmp.name

        try:
            loaded = load_yaml_file(tmp_path)
            self.assertEqual(loaded, {})
        finally:
            os.remove(tmp_path)

    # Tests for merge_dict
    def test_merge_dict_simple(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 3, "c": 4}
        result = merge_dict(d1, d2)
        self.assertEqual(result, {"a": 1, "b": 3, "c": 4})

    def test_merge_dict_nested(self):
        d1 = {"a": {"x": 1}, "b": 2}
        d2 = {"a": {"y": 2}, "c": 3}
        result = merge_dict(d1, d2)
        self.assertEqual(result, {"a": {"x": 1, "y": 2}, "b": 2, "c": 3})

    def test_merge_dict_overwrite_non_dict(self):
        d1 = {"a": {"x": 1}}
        d2 = {"a": 5}  # overwrite dict with int
        result = merge_dict(d1, d2)
        self.assertEqual(result, {"a": 5})


# generate_chat_title_from_input.py
class TestGenerateChatTitle(unittest.IsolatedAsyncioTestCase):
    """Async tests for generating chat titles from LLM responses."""

    async def test_generate_chat_title_with_content(self):
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "Sample Title"
        mock_response.usage_metadata = {"tokens": 10}

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value=mock_response)

        conversation = "This is a test conversation"
        title, metadata = await generate_chat_title_from_input(
            mock_llm, conversation
        )

        # Debug info (always shown)
        self.addCleanup(
            print, f"[DEBUG] Prompt sent: {mock_llm.invoke.call_args[0][0]}"
        )

        # Assertions
        self.assertEqual(title, "Sample Title")
        self.assertEqual(metadata, {"tokens": 10})

    async def test_generate_chat_title_without_content(self):
        # Mock response without content
        mock_response = Mock()
        mock_response.usage_metadata = {"tokens": 5}
        if hasattr(mock_response, "content"):
            delattr(mock_response, "content")  # simulate missing attribute

        # Mock LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(return_value=mock_response)

        conversation = "Another conversation"
        title, metadata = await generate_chat_title_from_input(
            mock_llm, conversation
        )

        # Debug info (always shown)
        self.addCleanup(
            print, f"[DEBUG] Prompt sent: {mock_llm.invoke.call_args[0][0]}"
        )
        # Assertions
        self.assertEqual(title, "New Chat")
        self.assertEqual(metadata, {"tokens": 5})


# get_log.py
class TestLoggingUtils(unittest.TestCase):
    """Unit tests for logging utility functions and logger configuration."""

    @patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"})
    def test_get_log_level_debug(self):
        self.assertEqual(get_log_level(), logging.DEBUG)

    @patch.dict("os.environ", {"LOG_LEVEL": "INFO"})
    def test_get_log_level_info(self):
        self.assertEqual(get_log_level(), logging.INFO)

    @patch.dict("os.environ", {"LOG_LEVEL": "WARNING"})
    def test_get_log_level_warning(self):
        self.assertEqual(get_log_level(), logging.WARNING)

    @patch.dict("os.environ", {"LOG_LEVEL": "ERROR"})
    def test_get_log_level_error(self):
        self.assertEqual(get_log_level(), logging.ERROR)

    @patch.dict("os.environ", {"LOG_LEVEL": "CRITICAL"})
    def test_get_log_level_critical(self):
        self.assertEqual(get_log_level(), logging.CRITICAL)

    @patch.dict("os.environ", {"LOG_LEVEL": "INVALID"})
    def test_get_log_level_invalid_defaults_to_info(self):
        # Invalid value should default to INFO
        self.assertEqual(get_log_level(), logging.INFO)

    @patch.dict("os.environ", {}, clear=True)
    def test_get_log_level_not_set_defaults_to_info(self):
        # If env var not set → INFO
        self.assertEqual(get_log_level(), logging.INFO)

    def test_get_logger_returns_logger_instance(self):
        logger = get_logger("test_module")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test_module")

    def test_logger_inherits_config(self):
        logger = get_logger("test_logger")
        with self.assertLogs(logger, level="INFO") as cm:
            logger.info("Test message")
        self.assertIn("Test message", cm.output[0])


# get_time_taken_message.py
class TestTimeUtils(unittest.TestCase):
    """Unit tests for time calculation and formatting utilities."""

    def test_seconds_only(self):
        start = 100.0
        with patch("time.perf_counter", return_value=start + 5):
            msg = get_time_taken_message(start)
        self.assertIn("5 seconds", msg)

    def test_one_second(self):
        start = 200.0
        with patch("time.perf_counter", return_value=start + 1):
            msg = get_time_taken_message(start)
        self.assertIn("1 second", msg)

    def test_minutes_and_seconds(self):
        start = 300.0
        with patch("time.perf_counter", return_value=start + 125):
            msg = get_time_taken_message(start)
        self.assertIn("2 minutes 5 seconds", msg)

    def test_exactly_one_minute(self):
        start = 400.0
        with patch("time.perf_counter", return_value=start + 60):
            msg = get_time_taken_message(start)
        self.assertIn("1 minute 0 seconds", msg)

    def test_zero_elapsed(self):
        start = 500.0
        with patch("time.perf_counter", return_value=start):
            msg = get_time_taken_message(start)
        self.assertIn("0 seconds", msg)


# get_username.py
class TestGetUsername(unittest.TestCase):
    """Unit tests for user display name normalization utility."""

    def test_with_valid_display_name(self):
        """Should return title-cased display name"""
        user = Mock()
        user.display_name = "User1"
        result = get_username(user)
        self.assertEqual(result, "User1")

    def test_with_uppercase_display_name(self):
        """Should normalize case to Title format"""
        user = Mock()
        user.display_name = "BOB"
        result = get_username(user)
        self.assertEqual(result, "Bob")

    def test_with_mixed_case_display_name(self):
        """Should correctly title-case mixed input"""
        user = Mock()
        user.display_name = "charLie"
        result = get_username(user)
        self.assertEqual(result, "Charlie")

    def test_with_none_display_name(self):
        """Should fall back to 'there' if display name is None"""
        user = Mock()
        user.display_name = None
        result = get_username(user)
        self.assertEqual(result, "there")

    def test_with_empty_string_display_name(self):
        """Should return empty string when display name is empty string"""
        user = Mock()
        user.display_name = ""
        result = get_username(user)
        # "" is not None, so title() is applied (still returns "")
        self.assertEqual(result, "")


class TestCustomMsgpackDefault(unittest.TestCase):
    """Unit tests for custom msgpack serialization logic."""

    def test_tool_message_serialization(self):
        """Should correctly serialize ToolMessage into dict"""
        tool_msg = ToolMessage(
            content="Tool response",
            name="my_tool",
            id="12345",
            tool_call_id="abc123",
            artifact={"key": "value"},
        )

        result = _custom_msgpack_default(tool_msg)

        expected = {
            "type": "tool",
            "content": "Tool response",
            "name": "my_tool",
            "id": "12345",
            "tool_call_id": "abc123",
            "artifact": str({"key": "value"}),  # gets stringified
        }
        self.assertEqual(result, expected)

    def test_non_tool_message_fallback(self):
        """Should delegate to original _msgpack_default for non-ToolMessage"""
        dummy_obj = {"x": 1}

        with patch("src.utils.serializer._original_default") as mock_default:
            mock_default.return_value = "serialized"
            result = _custom_msgpack_default(dummy_obj)

        mock_default.assert_called_once_with(dummy_obj)
        self.assertEqual(result, "serialized")


# text.py
class TestFileUtils(unittest.TestCase):
    """Unit tests for file utility functions (is_text_file, read_txt_file, etc)."""

    # ---- is_text_file ----
    def test_is_text_file_true(self):
        with patch("mimetypes.guess_type", return_value=("text/plain", None)):
            self.assertTrue(is_text_file("file.txt"))

    def test_is_text_file_false(self):
        with patch(
            "mimetypes.guess_type", return_value=("application/pdf", None)
        ):
            self.assertFalse(is_text_file("file.pdf"))

    def test_is_text_file_none(self):
        with patch("mimetypes.guess_type", return_value=(None, None)):
            self.assertFalse(is_text_file("unknown.bin"))

    # ---- read_txt_file ----
    @patch("builtins.open", new_callable=mock_open, read_data="Hello world")
    def test_read_txt_file(self, mock_file):
        content = read_txt_file("dummy.txt")
        self.assertEqual(content, "Hello world")
        mock_file.assert_called_once_with("dummy.txt", "r", encoding="utf-8")

    # ---- read_docx_file ----
    @patch("src.utils.summarizer.DocxDocument")
    def test_read_docx_file(self, mock_docx):
        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            MagicMock(text="Para1"),
            MagicMock(text="Para2"),
        ]
        mock_docx.return_value = mock_doc

        content = read_docx_file("dummy.docx")
        self.assertEqual(content, "Para1\nPara2")
        mock_docx.assert_called_once_with("dummy.docx")

    # ---- read_pdf_file ----
    @patch("src.utils.summarizer.PyPDFLoader")
    def test_read_pdf_file(self, mock_loader_class):
        mock_loader = MagicMock()
        mock_loader.load_and_split.return_value = [
            MagicMock(page_content="Page1"),
            MagicMock(page_content="Page2"),
        ]
        mock_loader_class.return_value = mock_loader

        content = read_pdf_file("dummy.pdf")
        self.assertEqual(content, "Page1 Page2")
        mock_loader_class.assert_called_once_with("dummy.pdf")

    # ---- read_attachment ----
    @patch("os.path.exists", return_value=False)
    def test_read_attachment_file_not_found(self, mock_exists):
        self.assertIsNone(read_attachment("missing.txt"))

    @patch("src.utils.summarizer.is_text_file", return_value=True)
    @patch("src.utils.summarizer.read_txt_file", return_value="Sample text")
    @patch("os.path.exists", return_value=True)
    def test_read_attachment_txt(self, mock_exists, mock_read, mock_is_text):
        result = read_attachment("file.txt")
        self.assertEqual(result, "Sample text")

    @patch("src.utils.summarizer.read_docx_file", return_value="Docx text")
    @patch("os.path.exists", return_value=True)
    def test_read_attachment_docx(self, mock_exists, mock_read):
        result = read_attachment("file.docx")
        self.assertEqual(result, "Docx text")

    @patch("src.utils.summarizer.read_pdf_file", return_value="Pdf text")
    @patch("os.path.exists", return_value=True)
    def test_read_attachment_pdf(self, mock_exists, mock_read):
        result = read_attachment("file.pdf")
        self.assertEqual(result, "Pdf text")

    @patch("os.path.exists", return_value=True)
    def test_read_attachment_unsupported_extension(self, mock_exists):
        result = read_attachment("file.jpg")
        self.assertIsNone(result)

    @patch("src.utils.summarizer.is_text_file", return_value=True)
    @patch(
        "src.utils.summarizer.read_txt_file",
        return_value="X" * (MAX_INPUT_CHARS + 10),
    )
    @patch("os.path.exists", return_value=True)
    def test_read_attachment_truncates(
        self, mock_exists, mock_read, mock_is_text
    ):
        result = read_attachment("file.txt")
        self.assertEqual(len(result), MAX_INPUT_CHARS)

    @patch("src.utils.summarizer.is_text_file", return_value=True)
    @patch("src.utils.summarizer.read_txt_file", side_effect=Exception("Boom"))
    @patch("os.path.exists", return_value=True)
    def test_read_attachment_handles_errors(
        self, mock_exists, mock_read, mock_is_text
    ):
        result = read_attachment("file.txt")
        self.assertIsNone(result)


# text.py
class TestCleanXMLTagParser(unittest.TestCase):
    """Unit tests for CleanXMLTagParser text cleaning functionality."""

    def setUp(self):
        self.parser = CleanXMLTagParser()

    def test_parser_removes_simple_tags(self):
        text = "<thinking>This is internal</thinking> Output"
        result = self.parser.parse(text)
        self.assertEqual(result, "This is internal Output")

    def test_parser_removes_tags_with_attributes(self):
        text = "<thinking step=1>Reasoning</thinking> Final"
        result = self.parser.parse(text)
        self.assertEqual(result, "Reasoning Final")

    def test_parser_with_list_input(self):
        text = ["<thinking>Hidden</thinking>", "Visible"]
        result = self.parser.parse(text)
        self.assertEqual(result, "Hidden Visible")

    def test_parser_removes_multiple_tags(self):
        text = (
            "<thinking>Step 1</thinking> then <thinking>Step 2</thinking> Done"
        )
        result = self.parser.parse(text)
        self.assertEqual(result, "Step 1 then Step 2 Done")

    def test_parser_returns_cleaned_text_no_tags(self):
        text = "Normal text only"
        result = self.parser.parse(text)
        self.assertEqual(result, "Normal text only")


class TestGetCollectionName(unittest.TestCase):
    """Unit tests for collection name generation utility."""

    def test_default_collection_name(self):
        result = get_collection_name()
        self.assertEqual(result, "chat_history")
        self.assertTrue(3 <= len(result) <= 512)

    def test_with_suffix(self):
        result = get_collection_name(suffix="user1")
        self.assertEqual(result, "chat_history_user1")

    def test_strips_invalid_start_and_end(self):
        result = get_collection_name(name="!!badname##")
        self.assertEqual(result, "badname")
        self.assertTrue(result[0].isalnum())
        self.assertTrue(result[-1].isalnum())

    def test_length_truncation(self):
        long_suffix = "x" * 600
        result = get_collection_name(suffix=long_suffix)
        self.assertEqual(len(result), 512)

    def test_minimum_length_padding(self):
        result = get_collection_name(name="a")
        self.assertGreaterEqual(len(result), 3)
        self.assertTrue(result.startswith("a"))

    def test_with_numeric_name(self):
        result = get_collection_name(name="123chat")
        self.assertTrue(result.startswith("123chat"))

    def test_only_invalid_characters(self):
        result = get_collection_name(name="!!!")
        self.assertGreaterEqual(len(result), 3)
        self.assertSetEqual(set(result), {"_"})


# usage.py
class TestGetUsageCostDetails(unittest.TestCase):
    """Unit tests for usage cost calculation utility."""

    def test_calculates_costs_correctly(self):
        usage = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
        }
        result = get_usage_cost_details(usage, 0.002, 0.004)

        self.assertEqual(result["input_tokens"], 1000)
        self.assertEqual(result["output_tokens"], 500)
        self.assertEqual(result["total_tokens"], 1500)
        self.assertAlmostEqual(
            result["input_cost"], 0.002
        )  # 1000/1000 * 0.002
        self.assertAlmostEqual(
            result["output_cost"], 0.002
        )  # 500/1000 * 0.004
        self.assertAlmostEqual(result["total_cost"], 0.004)

    def test_defaults_when_keys_missing(self):
        usage = {}
        result = get_usage_cost_details(usage, 0.01, 0.01)

        self.assertEqual(result["input_tokens"], 0)
        self.assertEqual(result["output_tokens"], 0)
        self.assertEqual(result["total_tokens"], 0)
        self.assertEqual(result["total_cost"], 0.0)


class TestSendUsageCostMessage(unittest.TestCase):
    """Unit tests for usage cost message formatting utility."""

    def test_message_formatting(self):
        usage = {
            "input_tokens": 2000,
            "output_tokens": 1000,
            "total_tokens": 3000,
        }
        msg = send_usage_cost_message(usage, 0.01, 0.02)

        self.assertIn("📦 Token usage", msg)
        self.assertIn("Total Input tokens: 2000", msg)
        self.assertIn("Total Output tokens: 1000", msg)
        self.assertIn("Total tokens: 3000", msg)
        self.assertIn("Input cost: $0.020000", msg)  # (2000/1000)*0.01
        self.assertIn("Output cost: $0.020000", msg)  # (1000/1000)*0.02
        self.assertIn("Total cost: $0.040000", msg)


class TestLogUsageDetails(unittest.TestCase):
    """Unit tests for logging usage details."""

    @patch("src.utils.usage.logger")
    def test_logs_with_user(self, mock_logger):
        usage = {
            "input_tokens": 100,
            "output_tokens": 200,
            "total_tokens": 300,
        }
        mock_user = MagicMock()
        mock_user.id = "user123"

        log_usage_details(usage, 0.01, 0.02, mock_user)

        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_with(
            "Logged in user: %s | Cost: $%.6f", "user123", unittest.mock.ANY
        )

    @patch("src.utils.usage.logger")
    def test_logs_without_user(self, mock_logger):
        usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        log_usage_details(usage, 0.01, 0.02, None)

        mock_logger.info.assert_called_with(
            "Logged in user: %s | Cost: $%.6f", "unknown", 0.0
        )


class TestLogAndShowUsageDetails(unittest.IsolatedAsyncioTestCase):
    """Async tests for logging and showing usage details in chat."""

    @patch("src.utils.usage.send_usage_cost_message")
    @patch("src.utils.usage.logger")
    @patch("src.utils.usage.cl.Message")
    @patch("src.utils.usage.cl.user_session")
    async def test_log_and_show_usage_details_sends_message(
        self, mock_user_session, mock_message, mock_logger, mock_send_msg
    ):
        profiles = {
            "default": {
                "cost": {"input_token_cost": 0.01, "output_token_cost": 0.02}
            }
        }
        usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}

        mock_user_session.get.side_effect = lambda key: {
            "chat_profile": "default",
            "user": MagicMock(identifier="user123", id="user123"),
        }[key]

        mock_msg = AsyncMock()
        mock_message.return_value = mock_msg

        await log_and_show_usage_details(
            profiles, usage, chat_profile="default", env="dev"
        )

        mock_send_msg.assert_called_once()
        mock_msg.send.assert_awaited_once()
        mock_logger.info.assert_any_call("input token cost is %s", 0.01)
        mock_logger.info.assert_any_call("output token cost is %s", 0.02)

    @patch("src.utils.usage.logger")
    @patch("src.utils.usage.cl.user_session")
    async def test_log_and_show_usage_details_skips_slack_user(
        self, mock_user_session, mock_logger
    ):
        profiles = {
            "default": {
                "cost": {"input_token_cost": 0.01, "output_token_cost": 0.02}
            }
        }
        usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        mock_user_session.get.side_effect = lambda key: {
            "chat_profile": "default",
            "user": MagicMock(identifier="slack_user", id="slack_user"),
        }[key]
        await log_and_show_usage_details(
            profiles, usage, chat_profile="default", env="dev"
        )
        mock_logger.info.assert_any_call("input token cost is %s", 0.01)
        mock_logger.info.assert_any_call("output token cost is %s", 0.02)


# profile_loader.py
class TestLoadChatProfiles(unittest.IsolatedAsyncioTestCase):
    """Async tests for loading chat profiles from configuration."""

    @patch("src.utils.profile_loader.get_username", return_value="TestUser")
    async def test_load_chat_profiles_single_profile(self, mock_get_username):
        user = MagicMock(spec=cl.User)
        profiles_cfg = {"default": {"icon": "🙂", "starters": ["starter1"]}}
        starters_cfg = {
            "starter1": {
                "name": "Hello",
                "message": "Hi there!",
                "label": "Hello",
            }
        }

        profiles = await load_chat_profiles(user, profiles_cfg, starters_cfg)

        self.assertEqual(len(profiles), 1)
        profile = profiles[0]
        self.assertIsInstance(profile, cl.ChatProfile)
        self.assertEqual(profile.name, "default")
        self.assertEqual(profile.icon, "🙂")
        self.assertIn("Hello *TestUser*", profile.markdown_description)
        self.assertEqual(len(profile.starters), 1)
        self.assertEqual(profile.starters[0].label, "Hello")
        self.assertEqual(profile.starters[0].message, "Hi there!")

    @patch("src.utils.profile_loader.get_username", return_value="Guest")
    async def test_load_chat_profiles_multiple_profiles(
        self, mock_get_username
    ):
        user = MagicMock(spec=cl.User)
        profiles_cfg = {
            "assistant": {"icon": "🤖", "starters": ["s1", "s2"]},
            "helper": {"icon": "🧑", "starters": []},
        }
        starters_cfg = {
            "s1": {
                "name": "Ask",
                "message": "How can I help?",
                "label": "Ask",
            },
            "s2": {
                "name": "Info",
                "message": "Here's some info",
                "label": "Info",
            },
        }

        profiles = await load_chat_profiles(user, profiles_cfg, starters_cfg)

        self.assertEqual(len(profiles), 2)

        # First profile checks
        assistant = profiles[0]
        self.assertEqual(assistant.name, "assistant")
        self.assertEqual(assistant.icon, "🤖")
        self.assertIn("Hello *Guest*", assistant.markdown_description)
        self.assertEqual(len(assistant.starters), 2)

        # Second profile checks
        helper = profiles[1]
        self.assertEqual(helper.name, "helper")
        self.assertEqual(helper.icon, "🧑")
        self.assertEqual(len(helper.starters), 0)

    @patch("src.utils.profile_loader.get_username", return_value="UserX")
    async def test_load_chat_profiles_empty_config(self, mock_get_username):
        user = MagicMock(spec=cl.User)
        profiles_cfg = {}
        starters_cfg = {}

        profiles = await load_chat_profiles(user, profiles_cfg, starters_cfg)

        self.assertEqual(len(profiles), 0)


class TestGitUtils(unittest.IsolatedAsyncioTestCase):
    """Unit and async tests for git utility functions
    (ignore_patterns, copy_items, clone_repo, etc)."""

    def setUp(self):
        # Create temp directories for src/dst testing
        self.temp_src = tempfile.mkdtemp()
        self.temp_dst = tempfile.mkdtemp()
        # Create dummy files/folders
        with open(
            os.path.join(self.temp_src, "file.txt"), "w", encoding="utf-8"
        ) as f:
            f.write("test")
        os.mkdir(
            os.path.join(self.temp_src, "__pycache__")
        )  # should be excluded

    def tearDown(self):
        shutil.rmtree(self.temp_src, ignore_errors=True)
        shutil.rmtree(self.temp_dst, ignore_errors=True)

    # ---------------- ignore_patterns ----------------
    def test_ignore_patterns(self):
        names = ["file.txt", "__pycache__", ".env"]
        ignored = git_utils.ignore_patterns(self.temp_src, names)
        self.assertIn("__pycache__", ignored)
        self.assertIn(".env", ignored)
        self.assertNotIn("file.txt", ignored)

    # ---------------- copy_items ----------------
    def test_copy_items(self):
        git_utils.copy_items(self.temp_src, self.temp_dst)
        copied_file = os.path.join(self.temp_dst, "file.txt")
        excluded_dir = os.path.join(self.temp_dst, "__pycache__")
        self.assertTrue(os.path.exists(copied_file))
        self.assertFalse(os.path.exists(excluded_dir))

    # ---------------- clone_repo ----------------
    @patch("src.utils.git.Repo.clone_from")
    async def test_clone_repo_success(self, mock_clone):
        repo_url = "https://github.com/test/repo.git"
        result = await git_utils.clone_repo(repo_url, "myrepo", replace=True)
        self.assertTrue(result["status"])
        self.assertIn("myrepo", result["path"])
        mock_clone.assert_called_once()

    @patch(
        "src.utils.git.Repo.clone_from",
        side_effect=GitCommandError("clone", "fail"),
    )
    async def test_clone_repo_failure(self, mock_clone):
        repo_url = "https://github.com/test/repo.git"
        result = await git_utils.clone_repo(repo_url, "badrepo", replace=True)
        self.assertFalse(result["status"])
        self.assertIn("Git error", result["msg"])

    # ---------------- commit_and_push_code ----------------
    @patch("src.utils.git.Repo")
    async def test_commit_and_push_code_success(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_origin = MagicMock()
        mock_repo.remote.return_value = mock_origin
        mock_repo_cls.return_value = mock_repo

        os.environ["GITHUB_USERNAME"] = "user"
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "token"

        result = await git_utils.commit_and_push_code(
            "/tmp/repo", "https://github.com/test/repo.git"
        )
        self.assertTrue(result["status"])
        self.assertIn("/tmp/repo", result["path"])
        mock_origin.push.assert_called_once()

    @patch("src.utils.git.Repo", side_effect=GitCommandError("push", "fail"))
    async def test_commit_and_push_code_failure(self, mock_repo_cls):
        os.environ["GITHUB_USERNAME"] = "user"
        os.environ["GITHUB_PERSONAL_ACCESS_TOKEN"] = "token"

        result = await git_utils.commit_and_push_code(
            "/tmp/repo", "https://github.com/test/repo.git"
        )
        self.assertFalse(result["status"])
        self.assertIn("Git error", result["msg"])

    # ---------------- create_repo_from_boilerplate ----------------
    @patch(
        "src.utils.git.commit_and_push_code",
        new_callable=AsyncMock,
        return_value={"status": True, "msg": "", "path": "/tmp/repo"},
    )
    @patch("src.utils.git.copy_items")
    @patch(
        "src.utils.git.clone_repo",
        new_callable=AsyncMock,
        return_value={"status": True, "msg": "", "path": "/tmp/repo"},
    )
    async def test_create_repo_from_boilerplate_success(
        self, mock_clone, mock_copy, mock_commit
    ):
        result = await git_utils.create_repo_from_boilerplate(
            "myrepo", "https://github.com/test/repo.git", "react"
        )
        self.assertTrue(result["status"])
        self.assertIn("/tmp/repo", result["path"])
        mock_copy.assert_called_once()
        mock_commit.assert_called_once()

    @patch(
        "src.utils.git.clone_repo",
        new_callable=AsyncMock,
        side_effect=GitCommandError("clone", "fail"),
    )
    async def test_create_repo_from_boilerplate_failure(self, mock_clone):
        result = await git_utils.create_repo_from_boilerplate(
            "badrepo", "https://github.com/test/repo.git", "react"
        )
        self.assertFalse(result["status"])
        self.assertIn("Git error", result["msg"])

    # ---------------- get_git_details_from_input ----------------
    async def test_get_git_details_from_input_valid_json(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = '{"repo_name": "test", "repo_url": "https://github.com/test/repo.git"}'
        mock_llm.invoke.return_value.usage_metadata = {"tokens": 10}

        content, usage = await git_utils.get_git_details_from_input(
            mock_llm, "some conversation"
        )
        self.assertEqual(content["repo_name"], "test")
        self.assertIn("repo_url", content)
        self.assertEqual(usage, {"tokens": 10})

    async def test_get_git_details_from_input_extra_text(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = (
            'Here is result: {"repo_name": "demo", '
            '"repo_url": "https://github.com/demo/repo.git"} Done!'
        )
        mock_llm.invoke.return_value.usage_metadata = {"tokens": 5}

        content, usage = await git_utils.get_git_details_from_input(
            mock_llm, "conversation"
        )
        self.assertEqual(content["repo_name"], "demo")
        self.assertEqual(
            content["repo_url"], "https://github.com/demo/repo.git"
        )
        self.assertEqual(usage, {"tokens": 5})


if __name__ == "__main__":
    unittest.main(verbosity=2, buffer=False)  # buffer=False ensures print
