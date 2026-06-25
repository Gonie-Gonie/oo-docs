from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_apidoc_query_helpers_filter_find_and_group(tmp_path) -> None:
    api = collect_sample_api(tmp_path)

    assert api.modules_by_name()["samplepkg"].name == "samplepkg"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.Widget.render") is not None
    assert [obj.name for obj in api.select(kind="function")] == ["make_widget"]

    filtered = api.filtered(kind="class", module_prefix="samplepkg")
    assert filtered.find("samplepkg.Widget") is not None
    assert filtered.find("samplepkg.make_widget") is None
