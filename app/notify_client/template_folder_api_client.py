from app.extensions import redis_client
from app.notify_client import NotifyAdminAPIClient, cache


class TemplateFolderAPIClient(NotifyAdminAPIClient):

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

    def get_template_folder(self, service_id, folder_id):
        if folder_id is None:
            return {
                'id': None,
                'name': 'Templates',
                'parent_id': None,
            }
        else:
            return next(
                folder for folder in self.get_template_folders(service_id)
                if folder['id'] == str(folder_id)
            )

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

        if template_ids:
            redis_client.delete(*(f'service-{service_id}-template-{id}-version-None' for id in template_ids))

    @cache.delete('service-{service_id}-template-folders')
    def update_template_folder(self, service_id, template_folder_id, name, users_with_permission=None):
        data = {"name": name}
        if users_with_permission:
            data["users_with_permission"] = users_with_permission
        self.post(
            '/service/{}/template-folder/{}'.format(service_id, template_folder_id),
            data
        )

    @cache.delete('service-{service_id}-template-folders')
    def delete_template_folder(self, service_id, template_folder_id):
        self.delete('/service/{}/template-folder/{}'.format(service_id, template_folder_id), {})


template_folder_api_client = TemplateFolderAPIClient()
