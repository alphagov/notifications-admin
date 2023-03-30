from app.notify_client import NotifyAdminAPIClient


class TestBaseClient:
    def test_does_not_add_header_outside_request_context(self, notify_admin, mocker):
        api_client = NotifyAdminAPIClient()
        api_client.init_app(notify_admin)
        perform_request_mock = mocker.patch.object(api_client, "_perform_request")

        api_client.get("/mocked-request")

        request_kwargs = perform_request_mock.call_args_list[-1][0][2]
        headers = request_kwargs["headers"]
        assert "X-Notify-User-Id" not in headers

    def test_does_not_add_header_if_no_user_in_session(self, notify_admin, mocker):
        api_client = NotifyAdminAPIClient()
        api_client.init_app(notify_admin)
        perform_request_mock = mocker.patch.object(api_client, "_perform_request")

        with notify_admin.test_request_context():
            notify_admin.preprocess_request()  # Run `before_request`-decorated functions
            api_client.get("/mocked-request")

        request_kwargs = perform_request_mock.call_args_list[-1][0][2]
        headers = request_kwargs["headers"]
        assert "X-Notify-User-Id" not in headers

    def test_adds_notify_user_id_header_if_in_request_and_logged_in(
        self, notify_admin, active_user_with_permissions, mocker, fake_uuid
    ):
        api_client = NotifyAdminAPIClient()
        api_client.init_app(notify_admin)
        perform_request_mock = mocker.patch.object(api_client, "_perform_request")

        with notify_admin.test_request_context(), notify_admin.test_client() as client:
            client.login(active_user_with_permissions)
            notify_admin.preprocess_request()  # Run `before_request`-decorated functions
            api_client.get("/mocked-request")

        request_kwargs = perform_request_mock.call_args_list[-1][0][2]
        headers = request_kwargs["headers"]
        assert headers["X-Notify-User-Id"] == str(fake_uuid)
