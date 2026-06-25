from __future__ import annotations

import importlib.util

import pytest

from apidoc_samples import collect_sample_api


def test_griffe_collector_collects_general_package_tree(tmp_path) -> None:
    if importlib.util.find_spec("griffe") is None:
        pytest.skip("griffe is not installed")

    api = collect_sample_api(tmp_path, collector="griffe")

    assert api.metadata["collector"] == "griffe"
    assert api.find("samplepkg.Widget") is not None
    assert api.find("samplepkg.make_widget") is not None
