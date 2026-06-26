from __future__ import annotations

from apidoc_samples import collect_sample_api
from example_regression import assert_html_internal_links_resolve


def test_website_profile_builds_anchor_linked_html_reference(tmp_path) -> None:
    api = collect_sample_api(tmp_path)
    html_path = tmp_path / "website-api.html"
    widget = api.find_object("samplepkg.Widget")
    make_widget = api.find_object("samplepkg.make_widget")

    assert widget is not None
    assert make_widget is not None
    document = api.to_document(profile="website", max_level=2)

    assert document.validate(formats=("html",)).ok
    document.save_html(html_path)
    assert_html_internal_links_resolve(
        html_path,
        required_hrefs=(widget.anchor_name(), make_widget.anchor_name()),
        required_text=(
            "samplepkg API Reference",
            "samplepkg.Widget",
            "samplepkg.make_widget",
            "Source",
        ),
    )
