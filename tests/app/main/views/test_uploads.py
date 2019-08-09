from tests.conftest import SERVICE_ONE_ID


def test_get_upload_hub_page(client_request):
    client_request.get('main.uploads', service_id=SERVICE_ONE_ID)
