"""Centralized prompt/template management."""

from dataclasses import dataclass
from string import Formatter
from typing import Mapping


@dataclass(frozen=True)
class PromptTemplate:
    name: str
    system: str = ""
    user: str = ""

    def render(self, variables: Mapping[str, object] | None = None) -> tuple[str, str]:
        values = dict(variables or {})
        formatter = Formatter()

        def render_text(text: str) -> str:
            fields = {name for _, name, _, _ in formatter.parse(text) if name}
            missing = fields - values.keys()
            if missing:
                raise KeyError(f"Missing prompt variables: {sorted(missing)}")
            return text.format_map(values)

        return render_text(self.system), render_text(self.user)


class PromptManager:
    """Registry for named prompts so prompt text is not scattered across agents."""

    def __init__(self, templates: Mapping[str, PromptTemplate] | None = None) -> None:
        self._templates = dict(templates or {})

    def register(self, template: PromptTemplate) -> None:
        if not template.name.strip():
            raise ValueError("Prompt template name is required.")
        self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        try:
            return self._templates[name]
        except KeyError as exc:
            raise KeyError(f"Unknown prompt template: {name}") from exc
