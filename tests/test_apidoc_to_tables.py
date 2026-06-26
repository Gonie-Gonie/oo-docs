from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs.apidoc import ApiPresentationProfile
from oodocs.components.media import Table


def test_apidoc_package_and_module_tables_are_oodocs_tables(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    module = api.modules_by_name()["samplepkg"]

    assert isinstance(api.to_summary_table(api.public_objects()), Table)
    assert isinstance(api.to_modules_table(), Table)
    assert isinstance(api.to_issue_table(), Table)
    assert isinstance(module.to_summary_table(), Table)


def test_apidoc_parameter_table_uses_profile_columns(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    render = api.find("samplepkg.Widget.render")
    assert render is not None

    profile = ApiPresentationProfile(
        name="compact",
        parameter_columns=("name", "required", "source"),
    )
    table = render.to_parameters_table(profile=profile)

    assert table is not None
    assert [cell.content.plain_text() for cell in table.headers] == [
        "Name",
        "Required",
        "Source",
    ]
    assert [cell.content.plain_text() for cell in table.rows[0]] == [
        "path",
        "yes",
        "signature",
    ]
