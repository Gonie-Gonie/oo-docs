from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_inspect_collector_collects_general_package_tree(tmp_path) -> None:
    api = collect_sample_api(tmp_path, collector="inspect")

    assert api.metadata["collector"] == "inspect"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None
    assert api.classes()
    assert api.functions()
