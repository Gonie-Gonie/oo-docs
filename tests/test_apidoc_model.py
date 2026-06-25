from __future__ import annotations

from oodocs.apidoc import ApiModule, ApiObject, ApiPackage, ApiParameter, ApiReturn


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
