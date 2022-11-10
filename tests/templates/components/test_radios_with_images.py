import json


def test_govuk_frontend_jinja_overrides_on_design_system_v3():
    with open("package.json") as package_file:
        package_json = json.load(package_file)

    assert package_json["dependencies"]["govuk-frontend"].startswith("3."), (
        "After upgrading the Design System, manually validate that "
        "`app/templates/govuk_frontend_jinja_overrides/templates/components/*/template.html`"
        "are all structurally-correct and up-to-date macros. If not, update the macros or retire them and update the "
        "rendering process."
    )
