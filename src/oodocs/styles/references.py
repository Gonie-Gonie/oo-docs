"""Locale-aware templates for typed object references."""

from __future__ import annotations

from dataclasses import dataclass, field


REFERENCE_KINDS = (
    "part",
    "chapter",
    "section",
    "paragraph",
    "table",
    "figure",
    "equation",
    "code_block",
    "box",
    "countable",
)


@dataclass(frozen=True, slots=True)
class ReferenceTemplate:
    """Label and placement templates for one reference target kind."""

    singular_label: str
    plural_label: str | None = None
    template: str = "{label} {value}"
    plural_template: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "singular_label", str(self.singular_label))
        if self.plural_label is not None:
            object.__setattr__(self, "plural_label", str(self.plural_label))
        _validate_reference_template(self.template, "template")
        if self.plural_template is not None:
            _validate_reference_template(self.plural_template, "plural_template")

    def with_label(self, label: str) -> ReferenceTemplate:
        """Return this placement policy with a different singular label."""

        return ReferenceTemplate(
            singular_label=label,
            plural_label=None,
            template=self.template,
            plural_template=self.plural_template,
        )

    def format(self, value: str, *, label: str | None = None, plural: bool = False) -> str:
        """Format a reference value with singular or plural placement."""

        effective_label = self.singular_label if label is None else label
        template = self.plural_template if plural and self.plural_template else self.template
        return template.format(label=effective_label, value=value).strip()


def _validate_reference_template(template: str, name: str) -> None:
    text = str(template)
    if "{value}" not in text:
        raise ValueError(f"ReferenceTemplate.{name} must contain '{{value}}'")
    try:
        text.format(label="Label", value="1")
    except (KeyError, ValueError) as exc:
        raise ValueError(
            f"ReferenceTemplate.{name} supports only '{{label}}' and '{{value}}'"
        ) from exc


def _english_reference_templates() -> dict[str, ReferenceTemplate]:
    return {
        "part": ReferenceTemplate("Part"),
        "chapter": ReferenceTemplate("Chapter"),
        "section": ReferenceTemplate("Section"),
        "paragraph": ReferenceTemplate("Paragraph"),
        "table": ReferenceTemplate("Table"),
        "figure": ReferenceTemplate("Figure"),
        "equation": ReferenceTemplate("Equation"),
        "code_block": ReferenceTemplate("Code block", plural_label="Code blocks"),
        "box": ReferenceTemplate("Box", plural_label="Boxes"),
        "countable": ReferenceTemplate(""),
    }


@dataclass(slots=True)
class ReferenceDefaults:
    """Reference templates keyed by stable target-kind names."""

    templates: dict[str, ReferenceTemplate] = field(default_factory=_english_reference_templates)

    def __post_init__(self) -> None:
        normalized: dict[str, ReferenceTemplate] = {}
        for kind, template in self.templates.items():
            key = str(kind).strip()
            if key not in REFERENCE_KINDS:
                raise ValueError(f"Unsupported reference target kind: {kind!r}")
            if not isinstance(template, ReferenceTemplate):
                raise TypeError("ReferenceDefaults.templates values must be ReferenceTemplate objects")
            normalized[key] = template
        self.templates = normalized

    def template_for(self, kind: str) -> ReferenceTemplate:
        """Return a configured template or the English compatibility default."""

        if kind not in REFERENCE_KINDS:
            raise KeyError(kind)
        return self.templates.get(kind, _english_reference_templates()[kind])

    @classmethod
    def korean(cls) -> ReferenceDefaults:
        """Return Korean reference labels and suffix placement."""

        templates = _english_reference_templates()
        templates.update(
            {
                "part": ReferenceTemplate("부", plural_label="부", template="{value}{label}"),
                "chapter": ReferenceTemplate("장", plural_label="장", template="{value}{label}"),
                "section": ReferenceTemplate("절", plural_label="절", template="{value}{label}"),
                "paragraph": ReferenceTemplate("문단", plural_label="문단"),
                "table": ReferenceTemplate("표", plural_label="표"),
                "figure": ReferenceTemplate("그림", plural_label="그림"),
                "equation": ReferenceTemplate("식", plural_label="식"),
                "code_block": ReferenceTemplate("코드", plural_label="코드"),
                "box": ReferenceTemplate("상자", plural_label="상자"),
            }
        )
        return cls(templates)


__all__ = ["REFERENCE_KINDS", "ReferenceDefaults", "ReferenceTemplate"]
