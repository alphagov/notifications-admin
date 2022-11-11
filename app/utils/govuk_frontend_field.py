from flask import Markup, render_template_string


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
