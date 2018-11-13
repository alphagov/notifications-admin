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

    @cache.delete('service-{service_id}-template-folders')
    @cache.delete('service-{service_id}-templates')
    def move_to_folder(self, service_id, folder_id, template_ids, folder_ids):

        if folder_id:
            url = '/service/{}/template-folder/{}/contents'.format(service_id, folder_id)
        else:
            url = '/service/{}/template-folder/contents'.format(service_id)

        self.post(url, {
            'templates': list(template_ids),
            'folders': list(folder_ids),
        })

        self.redis_client.delete(*map(
            'template-{}-version-None'.format,
            template_ids,
        ))

    @cache.delete('service-{service_id}-template-folders')
    def update_template_folder(self, service_id, template_folder_id, name):
        self.post(
            '/service/{}/template-folder/{}'.format(service_id, template_folder_id),
            {"name": name}
        )

    @cache.delete('service-{service_id}-template-folders')
    def delete_template_folder(self, service_id, template_folder_id):
        self.post('/service/{}/template-folder/{}/delete'.format(service_id, template_folder_id))


template_folder_api_client = TemplateFolderAPIClient()
