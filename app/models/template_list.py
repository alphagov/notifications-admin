from app import format_notification_type


class TemplateList():

    def __init__(
        self,
        service,
        template_type='all',
        template_folder_id=None,
        user=None,
    ):
        self.service = service
        self.template_type = template_type
        self.template_folder_id = template_folder_id
        self.user = user

    def __iter__(self):
        for item in self.get_templates_and_folders(
            self.template_type, self.template_folder_id, self.user, ancestors=[]
        ):
            yield item

    def get_templates_and_folders(self, template_type, template_folder_id, user, ancestors):

        for item in self.get_template_folders(
            template_type, template_folder_id, user,
        ):
            yield TemplateListFolder(
                item,
                folders=self.get_template_folders(
                    template_type, item['id'], user
                ),
                templates=self.get_templates(
                    template_type, item['id']
                ),
                ancestors=ancestors,
                service_id=self.service.id,
            )
            for sub_item in self.get_templates_and_folders(
                template_type, item['id'], user, ancestors + [item]
            ):
                yield sub_item

        for item in self.get_templates(
            template_type, template_folder_id, user
        ):
            yield TemplateListTemplate(
                item,
                ancestors=ancestors,
                service_id=self.service.id,
            )

    def get_templates(self, template_type='all', template_folder_id=None, user=None):
        if user and template_folder_id:
            folder = self.service.get_template_folder(template_folder_id)
            if not user.has_template_folder_permission(folder):
                return []

        if isinstance(template_type, str):
            template_type = [template_type]
        if template_folder_id:
            template_folder_id = str(template_folder_id)
        return [
            template for template in self.service.all_templates
            if (set(template_type) & {'all', template['template_type']})
            and template.get('folder') == template_folder_id
        ]

    def get_user_template_folders(self, user):
        """Returns a modified list of folders a user has permission to view

        For each folder, we do the following:
        - if user has no permission to view the folder, skip it
        - if folder is visible and its parent is visible, we add it to the list of folders
        we later return without modifying anything
        - if folder is visible, but the parent is not, we iterate through the parent until we
        either find a visible parent or reach root folder. On each iteration we concatenate
        invisible parent folder name to the front of our folder name, modifying the name, and we
        change parent_folder_id attribute to a higher level parent. This flattens the path to the
        folder making sure it displays in the closest visible parent.

        """
        user_folders = []
        for folder in self.service.all_template_folders:
            if not user.has_template_folder_permission(folder, service=self.service):
                continue
            parent = self.service.get_template_folder(folder["parent_id"])
            if user.has_template_folder_permission(parent, service=self.service):
                user_folders.append(folder)
            else:
                folder_attrs = {
                    "id": folder["id"], "name": folder["name"], "parent_id": folder["parent_id"],
                    "users_with_permission": folder["users_with_permission"]
                }
                while folder_attrs["parent_id"] is not None:
                    folder_attrs["name"] = [
                        parent["name"],
                        folder_attrs["name"],
                    ]
                    if parent["parent_id"] is None:
                        folder_attrs["parent_id"] = None
                    else:
                        parent = self.service.get_template_folder(parent["parent_id"])
                        folder_attrs["parent_id"] = parent.get("id", None)
                        if user.has_template_folder_permission(parent, service=self.service):
                            break
                user_folders.append(folder_attrs)
        return user_folders

    def get_template_folders(self, template_type='all', parent_folder_id=None, user=None):
        if user:
            folders = self.get_user_template_folders(user)
        else:
            folders = self.service.all_template_folders
        if parent_folder_id:
            parent_folder_id = str(parent_folder_id)

        return [
            folder for folder in folders
            if (
                folder['parent_id'] == parent_folder_id
                and self.is_folder_visible(folder['id'], template_type, user)
            )
        ]

    def is_folder_visible(self, template_folder_id, template_type='all', user=None):

        if template_type == 'all':
            return True

        if self.get_templates(template_type, template_folder_id):
            return True

        if any(
            self.is_folder_visible(child_folder['id'], template_type, user)
            for child_folder in self.get_template_folders(template_type, template_folder_id, user)
        ):
            return True

        return False

    @property
    def as_id_and_name(self):
        return [(item.id, item.name) for item in self]

    @property
    def templates_to_show(self):
        return any(self)

    @property
    def folder_is_empty(self):
        return not any(self.get_templates_and_folders(
            'all', self.template_folder_id, self.user, []
        ))


class ServiceTemplateList(TemplateList):
    def __iter__(self):
        template_list_service = TemplateListService(
            self.service,
            templates=self.get_templates(
                template_folder_id=None,
            ),
            folders=self.get_template_folders(
                parent_folder_id=None,
            ),
        )

        yield template_list_service

        yield from self.get_templates_and_folders(
            self.template_type,
            self.template_folder_id,
            self.user,
            ancestors=[template_list_service]
        )


class TemplateLists():

    def __init__(self, user):
        self.services = sorted(
            user.services,
            key=lambda service: service.name.lower(),
        )
        self.user = user

    def __iter__(self):
        if len(self.services) == 1:
            yield from TemplateList(
                service=self.services[0],
                user=self.user,
            )
            return

        for service in self.services:
            yield from ServiceTemplateList(
                service=service,
                user=self.user,
            )

    @property
    def templates_to_show(self):
        return bool(self.services)


class TemplateListItem():

    is_service = False

    def __init__(
        self,
        template_or_folder,
        ancestors,
    ):
        self.id = template_or_folder['id']
        self.name = template_or_folder['name']
        self.ancestors = ancestors


class TemplateListTemplate(TemplateListItem):

    is_folder = False

    def __init__(
        self,
        template,
        ancestors,
        service_id,
    ):
        super().__init__(template, ancestors)
        self.service_id = service_id
        self.template_type = template['template_type']
        self.content = template.get('content')

    @property
    def hint(self):
        if self.template_type == 'broadcast':
            max_length_in_chars = 40
            if len(self.content) > (max_length_in_chars + 2):
                return self.content[:max_length_in_chars].strip() + '…'
            return self.content
        return format_notification_type(self.template_type) + ' template'


class TemplateListFolder(TemplateListItem):

    is_folder = True

    def __init__(
        self,
        folder,
        templates,
        folders,
        ancestors,
        service_id,
    ):
        super().__init__(folder, ancestors)
        self.folder = folder
        self.service_id = service_id
        self.folders = folders
        self.number_of_templates = len(templates)
        self.number_of_folders = len(folders)

    @property
    def _hint_parts(self):

        if self.number_of_folders == self.number_of_templates == 0:
            yield 'Empty'

        if self.number_of_templates == 1:
            yield '1 template'
        elif self.number_of_templates > 1:
            yield '{} templates'.format(self.number_of_templates)

        if self.number_of_folders == 1:
            yield '1 folder'
        elif self.number_of_folders > 1:
            yield '{} folders'.format(self.number_of_folders)

    @property
    def hint(self):
        return ', '.join(self._hint_parts)


class TemplateListService(TemplateListFolder):
    is_service = True

    def __init__(
        self,
        service,
        templates,
        folders,
    ):
        super().__init__(
            folder=service._dict,
            templates=templates,
            folders=folders,
            ancestors=[],
            service_id=service.id,
        )
