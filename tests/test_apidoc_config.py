from __future__ import annotations

from oodocs.apidoc import ApiBuildConfig, ApiCollectConfig, ApiDocstringParser, ApiPublicPolicy


def test_apidoc_config_roundtrip_supports_general_repo_policy(tmp_path) -> None:
    config = ApiBuildConfig(
        collection=ApiCollectConfig(
            collector="inspect",
            public_policy=ApiPublicPolicy.explicit("samplepkg.Widget"),
            docstring_style=ApiDocstringParser.google(),
            module_exclude_patterns=("samplepkg.tests*",),
        ),
        profile="website",
        output_formats=("html",),
        output_dir="artifacts/api",
        sidecars=True,
    )

    path = config.write_json(tmp_path / "apidoc-config.json")
    readback = ApiBuildConfig.read_json(path)

    assert readback.collection.public_policy == "explicit"
    assert readback.collection.explicit_names == ("samplepkg.Widget",)
    assert readback.collection.docstring_style == "google"
    assert readback.output_formats == ("html",)
