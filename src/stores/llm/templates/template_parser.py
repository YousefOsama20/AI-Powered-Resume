"""
TemplateParser
──────────────
Loads prompt templates from locale files (e.g., en/skill_extraction.py).
Supports multi-language prompts via the locales directory structure.

Adapted from the MiniRAG project's template_parser pattern.

Usage:
    parser = TemplateParser(language="en")
    prompt = parser.get("skill_extraction", "system_prompt", vars={})
"""

import os


class TemplateParser:

    def __init__(self, language: str = None, default_language: str = "en"):
        # Type: Sub-function
        """Initializes the parser with a language and default fallback."""
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None
        self.set_language(language)

    def set_language(self, language: str):
        # Type: Sub-function
        """Sets the active language, falling back to default if not found."""
        if not language:
            self.language = self.default_language
            return

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict = {}):
        # Type: Main function
        """
        Retrieves a prompt template by group and key.

        Args:
            group: Template group name (e.g., "skill_extraction", "apply_advice").
            key:   Template key within the group (e.g., "system_prompt").
            vars:  Dict of variables to substitute into the template.

        Returns:
            The rendered template string, or None if not found.
        """
        if not group or not key:
            return None

        # Try the requested language first
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py")
        targeted_language = self.language

        if not os.path.exists(group_path):
            # Fallback to default language
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py")
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return None

        # Dynamically import the template module
        module = __import__(
            f"stores.llm.templates.locales.{targeted_language}.{group}",
            fromlist=[group]
        )

        if not module:
            return None

        key_attribute = getattr(module, key)
        return key_attribute.substitute(vars)
