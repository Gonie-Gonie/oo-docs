from __future__ import annotations

from oodocs import Chapter, Document, Table
from oodocs.apidoc import (
    ApiExample,
    ApiModule,
    ApiObject,
    ApiPackage,
    ApiParameter,
    ApiException,
    ApiRendererNote,
    ApiReturn,
    ApiSeeAlso,
)


def test_apidoc_model_roundtrip_preserves_object_tree() -> None:
    obj = ApiObject(
        "function",
        "run",
        "samplepkg.run",
        "samplepkg",
        signature="run(path: str) -> str",
        summary="Run a task.",
        parameters=[ApiParameter("path", "str", description="Input path.")],
        returns=ApiReturn("str", "Input path.", documented=True),
    )
    api = ApiPackage("samplepkg", modules=[ApiModule("samplepkg", [obj])])

    readback = ApiPackage.from_dict(api.to_dict())
    found = readback.find("samplepkg.run")

    assert isinstance(found, ApiObject)
    assert found.parameters[0].annotation == "str"
    assert found.returns is not None
    assert found.returns.documented


def test_apidoc_leaf_metadata_helpers_compose_into_oodocs_blocks() -> None:
    returns = ApiReturn("typing.Sequence[str]", "Rendered paths.", documented=True)
    exception = ApiException("ValueError", "If the path is invalid.")
    example = ApiExample("print('ok')", caption="Minimal use", syntax_ok=True)
    see_also = ApiSeeAlso("save", target="samplepkg.save", kind="function")
    note = ApiRendererNote("html", "Adds stable anchors.", "info")

    table = Table(
        ["Kind", "Value", "Detail"],
        [
            ["Return", *returns.to_row(("type", "description"))],
            ["Raises", *exception.to_row()],
            ["Example", *example.to_row(("language", "caption"))],
            ["See also", *see_also.to_row(("label", "target"))],
            ["Renderer", *note.to_row(("output_format", "message"))],
        ],
    )
    document = Document(
        "Leaf Metadata",
        Chapter(
            "Details",
            returns.to_paragraph(),
            exception.to_paragraph(),
            example.to_paragraph(),
            example.to_code_block(),
            see_also.to_paragraph(),
            note.to_paragraph(),
            table,
        ),
    )

    assert returns.to_row(("type", "documented")) == ["Sequence[str]", "yes"]
    assert example.to_row(("syntax_ok", "doctest_ok")) == ["yes", ""]
    assert "Rendered paths." in returns.to_paragraph().plain_text()
    assert "ValueError" in exception.to_paragraph().plain_text()
    assert "Minimal use" in example.to_paragraph().plain_text()
    assert "samplepkg.save" in see_also.to_paragraph().plain_text()
    assert "Adds stable anchors." in note.to_paragraph().plain_text()
    assert document.validate(formats=("html",)).ok
