from app.notify_client import NotifyAdminAPIClient, cache


class TemplateFolderAPIClient(NotifyAdminAPIClient):
    # Fudge assert in the super __init__ so
    # we can set those variables later.
    def __init__(self):
        super().__init__('a' * 73, 'b')

    @cache.delete('service-{service_id}-template-folders')
    def create_template_folder(
        self,
        service_id,
        name,
        parent_id=None
    ):
        data = {
            'name': name,
            'parent_id': parent_id
        }
        return self.post('/service/{}/template-folder'.format(service_id), data)['data']['id']

    @cache.set('service-{service_id}-template-folders')
    def get_template_folders(self, service_id):
        return self.get('/service/{}/template-folder'.format(service_id))['template_folders']


template_folder_api_client = TemplateFolderAPIClient()
