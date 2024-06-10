from unittest import mock
from unittest.mock import PropertyMock

import pytest
from wtforms import Form


class ComparablePropertyMock(PropertyMock):
    """A minimal extension of PropertyMock that allows it to be compared against another value"""

    def __lt__(self, other):
        return self() < other


def check_render_template_forms(calls: list[mock.call]):
    for call in calls:
        template = call.args[1]
        context = call.args[2]

        # Specific exclusions to this check that a developer is manually overriding due to explicit handling.
        if template.name in {"views/uploads/preview.html", "views/letter-branding/manage-letter-branding.html"}:
            continue

        for key, value in context.items():
            if isinstance(value, Form) and key != "form":
                if key.startswith("_") and not value.errors:
                    # Forms passed in with a leading prefix are excluded from this check; the underscore implies the
                    # form won't throw errors. If it doesn't have errors then that's good; but if it does let's flag
                    # it.
                    continue

                raise ValueError(
                    f"{value} passed into `{template} as `{key}`. "
                    f"It should be passed as `form` if it is the main form for the page to allow for consistent error "
                    f"handling. If the form cannot report errors (eg it's a search form), you can prefix the key "
                    f"with an underscore to bypass this check.\n\n"
                    f"If you need to render multiple forms that can error on the page, you will need to override the "
                    f"`pageTitle` template block and handle `Error: ` prefixing and potentially error summaries "
                    f"yourself, then add an exclusion for that template to this check."
                )


def assert_mock_has_any_call_with_first_n_args(mocked, *args):
    if not any(call[0][: len(args)] == args for call in mocked.call_args_list):
        err_msg = "\n".join(
            (
                f"call{args} not found in Mock {mocked}",
                "  call_args_list: [",
                *[f"    {c}" for c in mocked.call_args_list],
                "  ]",
            )
        )
        pytest.fail(err_msg)
