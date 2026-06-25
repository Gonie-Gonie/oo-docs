from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_apidoc_object_converts_to_blocks(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    obj = api.find("samplepkg.make_widget")

    assert obj is not None
    blocks = obj.to_blocks(profile="reference")
    assert blocks
    assert obj.to_signature_block(profile="reference") in blocks
