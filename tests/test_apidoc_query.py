from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_apidoc_query_helpers_filter_find_and_group(tmp_path) -> None:
    api = collect_sample_api(tmp_path)

    assert api.modules_by_name()["samplepkg"].name == "samplepkg"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.Widget.render") is not None
    assert [obj.name for obj in api.select(kind="function")] == ["make_widget"]
    assert [obj.qualname for obj in api.properties()] == ["samplepkg.Widget.title"]

    filtered = api.filtered(kind="class", module_prefix="samplepkg")
    assert filtered.find("samplepkg.Widget") is not None
    assert filtered.find("samplepkg.make_widget") is None


def test_apidoc_module_query_helpers_scope_top_level_and_recursive_members(
    tmp_path,
) -> None:
    api = collect_sample_api(tmp_path)
    module = api.modules_by_name()["samplepkg"]

    assert [obj.qualname for obj in module.classes()] == ["samplepkg.Widget"]
    assert [obj.qualname for obj in module.functions()] == ["samplepkg.make_widget"]
    assert [obj.qualname for obj in module.attributes()] == ["samplepkg.CONSTANT"]
    assert [obj.qualname for obj in module.properties()] == ["samplepkg.Widget.title"]
    assert module.find("Widget") is module.find("samplepkg.Widget")

    top_level = module.select(kind=("class", "function"), recursive=False)
    recursive_members = module.select(kind=("method", "property"), recursive=True)

    assert [obj.qualname for obj in top_level] == [
        "samplepkg.Widget",
        "samplepkg.make_widget",
    ]
    assert [obj.qualname for obj in recursive_members] == [
        "samplepkg.Widget.title",
        "samplepkg.Widget.render",
    ]
