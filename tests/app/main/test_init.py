class TestJsonUpdatesBlueprint:
    def test_all_routes_return_401_for_unauthorised(self, notify_admin, client_request, fake_uuid):
        blueprint_rules = [
            rule for rule in notify_admin.url_map.iter_rules() if rule.endpoint.startswith("json_updates.")
        ]

        # These are only used to build the URL - they don't relate to any specific fixtures
        fake_params = {
            "service_id": fake_uuid,
            "notification_id": fake_uuid,
            "template_type": "email",
            "message_type": "email",
            "job_id": fake_uuid,
            "daily_limit_type": "email",
        }
        bad_views = []
        client_request.logout()
        for rule in blueprint_rules:
            try:
                client_request.get_response(
                    rule.endpoint, **{k: fake_params[k] for k in rule.arguments}, _expected_status=401
                )
            except AssertionError:
                bad_views.append(rule.endpoint)

        assert not bad_views, (
            f"Some json_updates blueprint views do not return a 401 for unauthorised clients: {bad_views}"
        )
