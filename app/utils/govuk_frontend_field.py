import copy
from abc import ABC, abstractmethod

from flask import Markup, render_template_string

from app.utils import merge_jsonlike


class GovukFrontendWidgetMixin(ABC):
    param_extensions = {}

    def __init__(self, label="", validators=None, param_extensions=None, **kwargs):
        super().__init__(label, validators, **kwargs)
        self._copy_params()
        merge_jsonlike(self.param_extensions, param_extensions)

    def _copy_params(self):
        """
        Make a deep copy of `self.param_extensions` to prevent different instances of fields accidentally modifying
        other fields on other forms.

        Fields are instantiated at a class level. This happens at a module level when the file is imported.

        ```
        class MyForm:
            my_field = MyField(param_extensions={'foo': 'bar'})
        ```

        However, through some flask magic, the `__init__` for that field doesn't get called at import time. An instance
        of "UnboundField" is called (which remembers the args and kwargs passed to the constructor). Later on when a
        form is constructed, at that point wtforms calls `unbound_field.bind` which ends up instantiating our form
        class.

        ```
        form_1 = MyForm()
        form_2 = MyForm()
        form_1.my_field != form_2.my_field
        form_1.my_field.param_extensions == form_2.my_field.param_extensions # (!!!!)
        ```

        The problem is that `param_extensions`, a dictionary that we merge in, might already be defined at a class level
        by a Field subclass. It might do this to set up some params specific to that field (such as a phone number field
        setting an input type of "tel").
        A second class of a text input field might set a label containing the header name.

        However, if we just call `merge_jsonlike`, we'll update self.param_extensions, which is actually still linked
        to all the other unbound fields sitting in memory waiting to be bound.

        This means that if you create two forms with the same type field and set param_extensions to different things,
        the second one you instantiate will end up with a merged dict containing both fields' params.

        The solution to this is to make a copy of the class level dictionary first. Then we've got the bound field with
        its own param_extensions, free to manipulate and modify as it needs to.
        """
        self.param_extensions = copy.deepcopy(self.param_extensions)

    @property
    @abstractmethod
    def govuk_frontend_component_name(self):
        """
        Should be a string matching a key in the `govuk_frontend_components` dict - which roughly
        matches up with URLs found in https://design-system.service.gov.uk/components/
        """
        pass

    def get_error_message(self, error_message_format="text"):
        if self.errors:
            return {
                "attributes": {
                    "data-notify-module": "track-error",
                    "data-error-type": self.errors[0],
                    "data-error-label": self.name,
                },
                error_message_format: self.errors[0],
            }
        else:
            return None

    def prepare_params(self, **kwargs):
        """
        Should return a dictionary that will be passed through to the macro as `params` for use within the component
        """
        return {}

    def widget(self, _field, **kwargs):
        """
        override the widget function, which is called from the html template when rendering

        see https://wtforms.readthedocs.io/en/3.0.x/widgets/
        """
        # widget always has a `field` param passed in as a positional, however, we're in a member function of a
        # Field class so can just discard it, `self == _field` is always true
        params = self.prepare_params(**kwargs)

        # override params with any sent in during instantiation
        merge_jsonlike(params, self.param_extensions)

        # override params with any sent in though use in templates
        merge_jsonlike(params, kwargs.get("param_extensions"))

        return render_govuk_frontend_macro(self.govuk_frontend_component_name, params)


def render_govuk_frontend_macro(component, params):
    """
    jinja needs a template to render but govuk_frontend_jinja only provides macros

    This function creates a template string that just calls the macro for `component` and returns the result.

    ```
    {%- from <path> import <macro> -%}

    {{ macro(params) }}
    ```

    This function dynamically fills in the path and macro based on the GOVUK_FRONTEND_MACROS dictionary.
    Then we render that template with any params to produce just the output of that macro.
    """
    govuk_frontend_components = {
        "radios": {"path": "govuk_frontend_jinja/components/radios/macro.html", "macro": "govukRadios"},
        "radios-with-images": {
            "path": "govuk_frontend_jinja_overrides/templates/components/radios-with-images/macro.html",
            "macro": "govukRadiosWithImages",
        },
        "text-input": {"path": "govuk_frontend_jinja/components/input/macro.html", "macro": "govukInput"},
        "textarea": {"path": "govuk_frontend_jinja/components/textarea/macro.html", "macro": "govukTextarea"},
        "checkbox": {
            "path": "govuk_frontend_jinja_overrides/templates/components/checkboxes/macro.html",
            "macro": "govukCheckboxes",
        },
    }

    # we need to duplicate all curly braces to escape them from the f string so jinja still sees them
    template_string = f"""
        {{%- from '{govuk_frontend_components[component]['path']}'
        import {govuk_frontend_components[component]['macro']} -%}}

        {{{{ {govuk_frontend_components[component]['macro']}(params) }}}}
    """

    return Markup(render_template_string(template_string, params=params))
