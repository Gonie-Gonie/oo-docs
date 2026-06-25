from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs.components.blocks import Section


def test_apidoc_object_converts_to_section(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    obj = api.find("samplepkg.Widget")

    assert obj is not None
    section = obj.to_section(level=2, profile="manual")
    assert isinstance(section, Section)
    assert section.title[0].plain_text() == "samplepkg.Widget"
