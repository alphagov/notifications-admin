

def test_should_return_verify_template(notifications_admin, notifications_admin_db):
    response = notifications_admin.test_client().get('/verify')

    assert response.status_code == 200
    assert 'Activate your account' in response.get_data(as_text=True)
