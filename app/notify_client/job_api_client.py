import uuid

from client.base import BaseAPIClient


class JobApiClient(BaseAPIClient):
    def __init__(self, base_url=None, client_id=None, secret=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             client_id=client_id or 'client_id',
                                             secret=secret or 'secret')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.client_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.secret = app.config['ADMIN_CLIENT_SECRET']

    def create_job(self, service_id, template_id, file_name):
        job_id = str(uuid.uuid4())
        data = {
            "id": job_id,
            "service": service_id,
            "template": template_id,
            "original_file_name": file_name,
            "bucket_name": "service-{}-notify".format(service_id),
            "file_name": "{}.csv".format(job_id)
        }

        resp = self.post(url='/service/{}/job'.format(service_id), data=data)
        return resp['data']
