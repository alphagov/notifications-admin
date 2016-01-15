def test_styleguide_can_render(app_):
    response = app_.test_client().get('/_styleguide')

    assert response.status_code == 200
