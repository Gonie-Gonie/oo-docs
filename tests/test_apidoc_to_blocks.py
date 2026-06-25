from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs import Box, Table
from oodocs.apidoc import ApiObject, ApiSeeAlso


def test_apidoc_object_converts_to_blocks(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    obj = api.find("samplepkg.make_widget")

    assert obj is not None
    blocks = obj.to_blocks(profile="reference")
    assert blocks
    assert obj.to_signature_block(profile="reference") in blocks


def test_manual_profile_renders_see_also_as_box() -> None:
    obj = ApiObject(
        "function",
        "load",
        "samplepkg.load",
        "samplepkg",
        see_also=[
            ApiSeeAlso(
                "save",
                target="samplepkg.save",
                kind="function",
                description="Persist a loaded object.",
            )
        ],
    )

    manual_blocks = obj.to_see_also_blocks(profile="manual")
    reference_blocks = obj.to_see_also_blocks(profile="reference")

    assert len(manual_blocks) == 1
    assert isinstance(manual_blocks[0], Box)
    assert "samplepkg.save" in manual_blocks[0].children[0].plain_text()
    assert len(reference_blocks) == 1
    assert isinstance(reference_blocks[0], Table)
