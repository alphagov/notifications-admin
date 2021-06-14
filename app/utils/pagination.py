from flask import request, url_for


def get_page_from_request():
    if 'page' in request.args:
        try:
            return int(request.args['page'])
        except ValueError:
            return None
    else:
        return 1


def generate_previous_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page - 1, 'Previous page', url_args or {})


def generate_next_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page + 1, 'Next page', url_args or {})


def generate_previous_next_dict(view, service_id, page, title, url_args):
    return {
        'url': url_for(view, service_id=service_id, page=page, **url_args),
        'title': title,
        'label': 'page {}'.format(page)
    }
