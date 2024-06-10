import itertools
from unittest import mock
from unittest.mock import MagicMock, PropertyMock

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


class RedisClientMock(MagicMock):
    """
    Provides a couple of helper functions for better assertions on functions like RedisClient.delete where calls can be
    duplicated without effect and delete can take multiple keys in one function call
    """

    def assert_called_with_args(self, *expected_keys: str):
        """
        Given a single arg, or a list of args, asserts that they were passed in as args to the mock at least once, in
        any call, in any positional place.

        Will fail if there are any args that were called but not specified in the assert
        """
        list_of_called_tuples = itertools.chain.from_iterable(call.args for call in self.call_args_list)
        set_of_actual_keys = set(list_of_called_tuples)
        if set(expected_keys) != set_of_actual_keys:
            msg = f"Expected '{self._mock_name}' to be called with {expected_keys}. Called with {set_of_actual_keys}"
            raise AssertionError(msg)

    def assert_called_with_subset_of_args(self, *expected_keys: str):
        """
        Given a single arg, or a list of args, asserts that they were passed in as args to the mock at least once, in
        any call, in any positional place

        Will fail if there are any args that were called but not specified in the assert

        Note this is designed for use with functions like RedisClient.delete where calls can be duplicated without
        effect and delete can take multiple keys in one function call
        """
        list_of_called_tuples = itertools.chain.from_iterable(call.args for call in self.call_args_list)

        set_of_actual_keys = set(list_of_called_tuples)
        set_of_expected_keys = set(expected_keys)
        if set_of_expected_keys - set_of_actual_keys:
            msg = (
                f"Expected '{self._mock_name}' to be called with at least {set_of_expected_keys}. "
                f"Called with {set_of_actual_keys}"
            )
            raise AssertionError(msg)
