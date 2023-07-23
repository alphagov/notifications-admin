from unittest import mock
from unittest.mock import PropertyMock

from wtforms import Form


class ComparablePropertyMock(PropertyMock):
    """A minimal extension of PropertyMock that allows it to be compared against another value"""

    def __lt__(self, other):
        return self() < other


def check_render_template_forms(calls: list[mock.call]):
    for call in calls:
        context = call.args[2]
        for key, value in context.items():
            if isinstance(value, Form) and key != "form":
                if key.startswith("_") and not value.errors:
                    # Forms passed in with a leading prefix are excluded from this check; the underscore implies the
                    # form won't throw errors. If it doesn't have errors then that's good; but if it does let's flag
                    # it.
                    continue

                raise ValueError(
                    f"{value} passed into `render_template` for `{call.args[1]} as `{key}`. "
                    f"It should be passed as `form` if it is the main form for the page to allow for consistent error "
                    f"handling. If the form cannot report errors (eg it's a search form), you can prefix the key "
                    f"with an underscore to bypass this check.\n\n"
                    f"If you need to render multiple forms that can error on the page, you will need to override the "
                    f"`pageTitle` template block and handle `Error: ` prefixing and potentially error summaries "
                    f"yourself, then add an exclusion for that template to this check."
                )
