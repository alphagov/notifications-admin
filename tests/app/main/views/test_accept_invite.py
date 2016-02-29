from flask import url_for


def test_existing_user_accept_invite_calls_api_and_redirects_to_dashboard(app_,
                                                                          service_one,
                                                                          sample_invite,
                                                                          mock_accept_invite,
                                                                          mock_get_user_by_email,
                                                                          mock_add_user_to_service):

    expected_service = service_one['id']
    expected_from_user = service_one['users'][0]
    expected_redirect_location = 'http://localhost/services/{}/dashboard'.format(expected_service)

    with app_.test_request_context():
        with app_.test_client() as client:

            response = client.get(url_for('main.accept_invite', token='thisisnotarealtoken'))

            mock_accept_invite.assert_called_with('thisisnotarealtoken')
            mock_get_user_by_email.assert_called_with('invited_user@test.gov.uk')
            mock_add_user_to_service.assert_called_with(expected_service,  expected_from_user, sample_invite)

            assert response.status_code == 302
            assert response.location == expected_redirect_location
