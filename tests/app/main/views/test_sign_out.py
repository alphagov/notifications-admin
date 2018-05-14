from flask import url_for


def test_render_sign_out_redirects_to_sign_in(
    client
):
    response = client.get(
        url_for('main.sign_out'))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.index', _external=True)


def test_sign_out_user(
    logged_in_client,
    mock_get_service,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
    mock_get_service_templates,
    mock_get_jobs,
    mock_has_permissions,
    mock_get_template_statistics,
    mock_get_service_statistics,
    mock_get_usage,
    mock_get_inbound_sms_summary,
):
    with logged_in_client.session_transaction() as session:
        assert session.get('user_id') is not None
    # Check we are logged in
    response = logged_in_client.get(
        url_for('main.service_dashboard', service_id="123"))
    assert response.status_code == 200
    response = logged_in_client.get(url_for('main.sign_out'))
    assert response.status_code == 302
    assert response.location == url_for(
        'main.index', _external=True)
    with logged_in_client.session_transaction() as session:
        assert session.get('user_id') is None
