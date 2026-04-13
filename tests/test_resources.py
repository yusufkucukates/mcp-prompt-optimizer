"""Tests for the TemplateManager resource manager.

Uses pytest's tmp_path fixture to isolate filesystem operations — no real
templates directory is required to run these tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.resources.template_manager import URI_SCHEME, TemplateManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manager(tmp_path: Path, md_files: dict[str, str] | None = None) -> TemplateManager:
    """Create a TemplateManager pointing at tmp_path, optionally pre-populating files."""
    if md_files:
        for name, content in md_files.items():
            (tmp_path / name).write_text(content, encoding="utf-8")
    return TemplateManager(templates_dir=tmp_path)


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------

class TestListTemplates:
    def test_returns_empty_list_for_empty_directory(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        assert manager.list_templates() == []

    def test_returns_one_entry_per_md_file(self, tmp_path: Path) -> None:
        manager = _make_manager(
            tmp_path,
            {"alpha.md": "# Alpha", "beta.md": "# Beta"},
        )
        templates = manager.list_templates()
        assert len(templates) == 2

    def test_entry_has_required_keys(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, {"my_template.md": "content"})
        entry = manager.list_templates()[0]
        assert "uri" in entry
        assert "name" in entry
        assert "mime_type" in entry

    def test_uri_uses_correct_scheme(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, {"dotnet_code_review.md": "content"})
        entry = manager.list_templates()[0]
        assert entry["uri"].startswith(f"{URI_SCHEME}://")

    def test_uri_contains_stem(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, {"dotnet_code_review.md": "content"})
        entry = manager.list_templates()[0]
        assert entry["uri"] == f"{URI_SCHEME}://dotnet_code_review"

    def test_name_is_stem_without_extension(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, {"debug_analysis.md": "content"})
        entry = manager.list_templates()[0]
        assert entry["name"] == "debug_analysis"

    def test_mime_type_is_text_markdown(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path, {"template.md": "content"})
        entry = manager.list_templates()[0]
        assert entry["mime_type"] == "text/markdown"

    def test_non_md_files_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("text file")
        (tmp_path / "data.json").write_text("{}")
        manager = _make_manager(tmp_path, {"real_template.md": "content"})
        templates = manager.list_templates()
        assert len(templates) == 1
        assert templates[0]["name"] == "real_template"

    def test_returns_entries_in_sorted_order(self, tmp_path: Path) -> None:
        manager = _make_manager(
            tmp_path,
            {"z_last.md": "", "a_first.md": "", "m_middle.md": ""},
        )
        names = [t["name"] for t in manager.list_templates()]
        assert names == sorted(names)

    def test_returns_empty_list_for_missing_directory(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent_subdir"
        manager = TemplateManager(templates_dir=missing)
        assert manager.list_templates() == []


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------

class TestGetTemplate:
    def test_returns_file_content(self, tmp_path: Path) -> None:
        content = "# My Template\n\nSome content here."
        manager = _make_manager(tmp_path, {"my_template.md": content})
        assert manager.get_template("my_template") == content

    def test_raises_file_not_found_for_missing_template(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with pytest.raises(FileNotFoundError):
            manager.get_template("nonexistent")

    def test_error_message_contains_template_name(self, tmp_path: Path) -> None:
        manager = _make_manager(tmp_path)
        with pytest.raises(FileNotFoundError, match="ghost_template"):
            manager.get_template("ghost_template")

    def test_reads_unicode_content(self, tmp_path: Path) -> None:
        unicode_content = "# Template\n\nHello 世界 — café résumé"
        manager = _make_manager(tmp_path, {"unicode.md": unicode_content})
        assert manager.get_template("unicode") == unicode_content

    def test_reads_multiline_content(self, tmp_path: Path) -> None:
        multiline = "# Title\n\n## Section 1\n\nParagraph one.\n\n## Section 2\n\nParagraph two."
        manager = _make_manager(tmp_path, {"multi.md": multiline})
        assert manager.get_template("multi") == multiline

    def test_path_traversal_is_blocked(self, tmp_path: Path) -> None:
        (tmp_path.parent / "secret.md").write_text("top secret", encoding="utf-8")
        manager = _make_manager(tmp_path)
        with pytest.raises(ValueError, match="path traversal"):
            manager.get_template("../secret")


# ---------------------------------------------------------------------------
# No caching (live disk reads)
# ---------------------------------------------------------------------------

class TestNoCaching:
    def test_reflects_updated_file_content(self, tmp_path: Path) -> None:
        path = tmp_path / "live.md"
        path.write_text("original content", encoding="utf-8")
        manager = TemplateManager(templates_dir=tmp_path)

        first_read = manager.get_template("live")
        assert first_read == "original content"

        # Modify the file after the first read
        path.write_text("updated content", encoding="utf-8")

        second_read = manager.get_template("live")
        assert second_read == "updated content", (
            "TemplateManager should not cache; updated content must be returned"
        )

    def test_new_file_appears_in_subsequent_list(self, tmp_path: Path) -> None:
        manager = TemplateManager(templates_dir=tmp_path)
        assert manager.list_templates() == []

        (tmp_path / "new_template.md").write_text("# New", encoding="utf-8")

        templates = manager.list_templates()
        assert len(templates) == 1
        assert templates[0]["name"] == "new_template"


# ---------------------------------------------------------------------------
# template_uri_to_name
# ---------------------------------------------------------------------------

class TestTemplateUriToName:
    def test_extracts_name_from_valid_uri(self, tmp_path: Path) -> None:
        manager = TemplateManager(templates_dir=tmp_path)
        assert manager.template_uri_to_name("prompt-template://dotnet_code_review") == "dotnet_code_review"

    def test_raises_value_error_for_wrong_scheme(self, tmp_path: Path) -> None:
        manager = TemplateManager(templates_dir=tmp_path)
        with pytest.raises(ValueError, match="Invalid template URI"):
            manager.template_uri_to_name("file:///some/path")

    def test_raises_value_error_for_empty_uri(self, tmp_path: Path) -> None:
        manager = TemplateManager(templates_dir=tmp_path)
        with pytest.raises(ValueError):
            manager.template_uri_to_name("")

    def test_raises_value_error_for_scheme_only_uri(self, tmp_path: Path) -> None:
        """prompt-template:// with no name after the scheme should be rejected."""
        manager = TemplateManager(templates_dir=tmp_path)
        with pytest.raises(ValueError, match="template name must not be empty"):
            manager.template_uri_to_name("prompt-template://")

    def test_raises_value_error_for_whitespace_name_uri(self, tmp_path: Path) -> None:
        manager = TemplateManager(templates_dir=tmp_path)
        with pytest.raises(ValueError, match="template name must not be empty"):
            manager.template_uri_to_name("prompt-template://   ")
