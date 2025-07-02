from app.commands import save_app_routes


def test_no_routes_removed_without_considering_redirects(notify_admin):
    """This test checks that we haven't removed any routes unexpectedly.

    It's OK to remove routes and just update this test, but if we do remove routes we should consider adding redirects
    so that users visiting the old URLs (eg if they've bookmarked them) don't get stranded."""
    try:
        save_app_routes(acknowledge_removed_routes=True)
    except ValueError as e:
        raise AssertionError(str(e)) from e
