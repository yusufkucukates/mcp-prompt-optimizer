"""MCP resource manager for prompt templates stored as markdown files on disk."""

from __future__ import annotations

from pathlib import Path

# URI scheme used for all template resources
URI_SCHEME = "prompt-template"

# Default templates directory: two levels above this file → project root / templates
_DEFAULT_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


class TemplateManager:
    """Manage prompt templates stored as .md files in a directory.

    Templates are loaded from disk on every read (no caching) so that
    in-place edits are reflected immediately without restarting the server.

    Args:
        templates_dir: Path to the directory containing .md template files.
                       Defaults to ``<project_root>/templates``.
    """

    def __init__(self, templates_dir: Path | None = None) -> None:
        self._dir: Path = templates_dir if templates_dir is not None else _DEFAULT_TEMPLATES_DIR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_templates(self) -> list[dict[str, str]]:
        """List all available template resources.

        Returns:
            A list of dicts, each containing:
                uri (str): Full resource URI, e.g. ``prompt-template://dotnet_code_review``.
                name (str): Template stem (filename without extension).
                mime_type (str): Always ``text/markdown``.
        """
        if not self._dir.is_dir():
            return []

        result: list[dict[str, str]] = []
        for path in sorted(self._dir.glob("*.md")):
            stem = path.stem
            result.append(
                {
                    "uri": f"{URI_SCHEME}://{stem}",
                    "name": stem,
                    "mime_type": "text/markdown",
                }
            )
        return result

    def get_template(self, name: str) -> str:
        """Read and return a template's markdown content.

        Args:
            name: Template stem (filename without the .md extension).

        Returns:
            The raw markdown content of the template file.

        Raises:
            FileNotFoundError: If no template with the given name exists.
            ValueError: If the name attempts to traverse outside the templates directory.
        """
        template_path = (self._dir / f"{name}.md").resolve()

        # Guard against path traversal (e.g. name="../../etc/passwd")
        try:
            template_path.relative_to(self._dir.resolve())
        except ValueError:
            raise ValueError(
                f"Invalid template name '{name}': "
                "path traversal outside the templates directory is not allowed."
            ) from None

        if not template_path.is_file():
            raise FileNotFoundError(
                f"Template '{name}' not found. "
                f"Expected file: {template_path}"
            )
        return template_path.read_text(encoding="utf-8")

    def template_uri_to_name(self, uri: str) -> str:
        """Extract the template name from a full resource URI.

        Args:
            uri: A URI of the form ``prompt-template://{name}``.

        Returns:
            The template name (stem).

        Raises:
            ValueError: If the URI does not match the expected scheme.
        """
        prefix = f"{URI_SCHEME}://"
        if not uri.startswith(prefix):
            raise ValueError(
                f"Invalid template URI '{uri}'. "
                f"Expected scheme: '{prefix}{{name}}'"
            )
        name = uri[len(prefix):]
        if not name.strip():
            raise ValueError(
                f"Invalid template URI '{uri}': template name must not be empty. "
                f"Expected format: '{prefix}{{name}}'"
            )
        return name
