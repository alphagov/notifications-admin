from urllib.parse import urlparse

from flask import request, session, url_for

from app import Service


def get_backlink_email_sender(service: Service, template_id: str):
    has_from_name = service.email_sender_name is not None
    has_reply_to = bool(service.email_reply_to_addresses)
    has_multiple_reply_to = len(service.email_reply_to_addresses) > 1

    args = {"service_id": service.id, "template_id": template_id}

    # Needs to choose from name
    if not has_from_name:
        base = ["view_template", "service_email_sender_change"]

        # 1a. clicks do this later -> add recipients
        # 1b. clicks add reply to email -> add recipients (endpoint will be added on the go)
        if not has_reply_to:
            expected_flow = base + ["service_email_reply_to"]
        # 2. choose reply to email -> add recipients
        elif has_multiple_reply_to:
            expected_flow = base + ["set_sender"]
        # 3. add recipients
        else:
            expected_flow = base
    # Needs to choose reply to email
    elif not has_reply_to:
        expected_flow = ["view_template", "service_email_reply_to"]

    # Has multiple reply to email
    elif has_multiple_reply_to:
        expected_flow = ["view_template", "set_sender"]
    # Contains all necessary fields and single reply to email (DONE)
    else:
        expected_flow = ["view_template"]

    return create_backlinks(expected_flow, **args)


def create_backlinks(routes, **kwargs):
    return [url_for(f"main.{route}", **kwargs) for route in routes]


def get_previous_backlink(service_id, template_id):
    if service_id is None or template_id is None:
        return None

    backlinks = session.get("email_sender_backlinks", [])

    current_path = request.path  # Just the path, no query string

    parsed_paths = [urlparse(url).path for url in backlinks]

    # Special journey check: user completed reply-to add and verify, now at step-0
    # In this case we are redirecting it back to view_template as too many values
    # have been set and we want to keep things consistent
    has_add_reply_to = any("email-reply-to/add" in path for path in parsed_paths)
    has_verify_reply_to = any("email-reply-to/" in path and "/verify" in path for path in parsed_paths)
    is_on_step_0 = "/one-off/step-0" in current_path

    if is_on_step_0 and has_add_reply_to and has_verify_reply_to:
        return url_for("main.view_template", service_id=service_id, template_id=template_id)

    try:
        paths = [urlparse(url).path for url in backlinks]
        current_index = paths.index(current_path)
        if current_index > 0:
            return backlinks[current_index - 1]
    except ValueError:
        pass

    return url_for("main.view_template", service_id=service_id, template_id=template_id)
