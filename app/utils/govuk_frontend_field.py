from abc import ABC, abstractmethod

from flask import Markup, render_template_string

from app.utils import merge_jsonlike


class GovukFrontendWidgetMixin(ABC):
    param_extensions = {}

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
