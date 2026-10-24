import sys
from unittest.mock import MagicMock, patch
import pytest

from scrapers.sorter import claude_classify, make_claude_classifier


LABELS = ["Construction", "IT", "Medical", "Real Estate & Leasing", "Other"]


def test_claude_classify_valid_label():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Construction"
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = claude_classify(
            title="Design and Construction of Hulhumale Jetty",
            labels=LABELS,
            api_key="test-key",
            model="claude-sonnet-4-5",
        )
        assert result == "Construction"
        mock_anthropic_module.Anthropic.assert_called_once_with(api_key="test-key")
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-5"
        assert "Construction, IT, Medical, Real Estate & Leasing, Other" in call_kwargs["messages"][0]["content"]


def test_claude_classify_unrecognized_label_fallback():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Agriculture"  # Not in LABELS
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response

    mock_anthropic_module = MagicMock()
    mock_anthropic_module.Anthropic.return_value = mock_client

    with patch.dict(sys.modules, {"anthropic": mock_anthropic_module}):
        result = claude_classify(
            title="Farming supplies",
            labels=LABELS,
            api_key="test-key",
        )
        assert result == "Other"


def test_make_claude_classifier():
    with patch("scrapers.sorter.claude_classify") as mock_classify:
        mock_classify.return_value = "IT"
        classifier = make_claude_classifier(labels=LABELS, api_key="custom-key", model="claude-test")
        
        result = classifier("Supply of Computer Systems")
        assert result == "IT"
        mock_classify.assert_called_once_with(
            "Supply of Computer Systems",
            labels=LABELS,
            api_key="custom-key",
            model="claude-test",
        )
