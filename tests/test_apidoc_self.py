from __future__ import annotations

from oodocs.apidoc import collect_api


def test_apidoc_collects_oodocs_public_api_for_self_reference() -> None:
    api = collect_api("oodocs", collector="auto", public_policy="__all__")

    assert api.name == "oodocs"
    assert api.find("oodocs.Document") is not None
    assert api.public_objects()
