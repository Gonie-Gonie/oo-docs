from __future__ import annotations

from apidoc_samples import collect_sample_api
from oodocs.components.media import Table


def test_apidoc_package_and_module_tables_are_oodocs_tables(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    module = api.modules_by_name()["samplepkg"]

    assert isinstance(api.to_summary_table(api.public_objects()), Table)
    assert isinstance(api.to_modules_table(), Table)
    assert isinstance(api.to_issue_table(), Table)
    assert isinstance(module.to_summary_table(), Table)
