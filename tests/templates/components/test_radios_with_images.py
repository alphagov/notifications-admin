import json
from importlib import metadata

import pytest
from packaging.version import Version


@pytest.mark.skip(reason="[NOTIFYNL] [TODO] REMOVE/RETEST AFTER SYNCING UPSTREAM")
def test_govuk_frontend_jinja_overrides_on_design_system_v5():
    with open("package.json") as package_file:
        package_json = json.load(package_file)
        govuk_frontend_version = Version(package_json["dependencies"]["govuk-frontend"])

    govuk_frontend_jinja_version = Version(metadata.version("govuk-frontend-jinja"))

    # Compatibility between these two libs is defined at https://github.com/LandRegistry/govuk-frontend-jinja/
    correct_govuk_frontend_version = Version("5.11.1") == govuk_frontend_version
    correct_govuk_frontend_jinja_version = Version("3.6.0") == govuk_frontend_jinja_version

    assert correct_govuk_frontend_version and correct_govuk_frontend_jinja_version, (
        "After upgrading either of the Design System packages, you must validate that "
        "`app/templates/govuk_frontend_jinja_overrides/templates/components/*/template.html`"
        "are all structurally-correct and up-to-date macros. If not, update the macros or retire them and update the "
        "rendering process."
    )
