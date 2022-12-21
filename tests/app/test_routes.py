import json


def test_record_changes_in_routes(notify_admin):
    """This test checks that we haven't removed any routes unexpectedly.

    It's OK to remove routes and just update this test, but if we do remove routes we should consider adding redirects
    so that users visiting the old URLs (eg if they've bookmarked them) don't get stranded."""
    current_routes = {r.rule for r in notify_admin.url_map.iter_rules()}
    with open("tests/route-list.json") as infile:
        expected_routes = set(json.load(infile))

    added_routes = current_routes.difference(expected_routes)
    removed_routes = expected_routes.difference(current_routes)

    error_messages = []

    if added_routes:
        error_messages.append(
            "\nNew routes have been added:\n"
            + "\n".join(f" -> {path}" for path in added_routes)
            + "\n\n"
            + "Run `flask command save-app-routes`."
        )

    if removed_routes:
        error_messages.append(
            "\nSome routes have been removed:\n"
            + "\n".join(f" -> {path}" for path in removed_routes)
            + "\n\n"
            + "Make sure there are appropriate redirects in place, and then run `flask command save-app-routes`."
        )

    assert not error_messages, "\n---".join(error_messages)
