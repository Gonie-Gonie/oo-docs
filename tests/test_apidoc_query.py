from __future__ import annotations

from apidoc_samples import collect_sample_api


def test_apidoc_query_helpers_filter_find_and_group(tmp_path) -> None:
    api = collect_sample_api(tmp_path)

    assert api.module_map()["samplepkg"].name == "samplepkg"
    assert api.find_object("samplepkg.Widget") is not None
    assert api.find_object("samplepkg.Widget.render") is not None
    assert [obj.name for obj in api.select_objects(kind="function")] == ["make_widget"]
    assert [obj.qualname for obj in api.select_properties()] == ["samplepkg.Widget.title"]

    filtered = api.subset(kind="class", module_prefix="samplepkg")
    assert filtered.find_object("samplepkg.Widget") is not None
    assert filtered.find_object("samplepkg.make_widget") is None


def test_apidoc_module_query_helpers_scope_top_level_and_recursive_members(
    tmp_path,
) -> None:
    api = collect_sample_api(tmp_path)
    module = api.module_map()["samplepkg"]

    assert [obj.qualname for obj in module.select_classes()] == ["samplepkg.Widget"]
    assert [obj.qualname for obj in module.select_functions()] == ["samplepkg.make_widget"]
    assert [obj.qualname for obj in module.select_attributes()] == ["samplepkg.CONSTANT"]
    assert [obj.qualname for obj in module.select_properties()] == ["samplepkg.Widget.title"]
    assert module.find_object("Widget") is module.find_object("samplepkg.Widget")

    top_level = module.select_objects(kind=("class", "function"), recursive=False)
    recursive_members = module.select_objects(kind=("method", "property"), recursive=True)

    assert [obj.qualname for obj in top_level] == [
        "samplepkg.Widget",
        "samplepkg.make_widget",
    ]
    assert [obj.qualname for obj in recursive_members] == [
        "samplepkg.Widget.title",
        "samplepkg.Widget.render",
    ]
