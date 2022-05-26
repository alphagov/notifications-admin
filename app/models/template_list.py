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

        for item in self.service.get_template_folders(
            template_type, template_folder_id, user,
        ):
            yield TemplateListFolder(
                item,
                folders=self.service.get_template_folders(
                    template_type, item['id'], user
                ),
                templates=self.service.get_templates(
                    template_type, item['id']
                ),
                ancestors=ancestors,
                service_id=self.service.id,
            )
            for sub_item in self.get_templates_and_folders(
                template_type, item['id'], user, ancestors + [item]
            ):
                yield sub_item

        for item in self.service.get_templates(
            template_type, template_folder_id, user
        ):
            yield TemplateListTemplate(
                item,
                ancestors=ancestors,
                service_id=self.service.id,
            )

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
            templates=self.service.get_templates(
                template_folder_id=None,
            ),
            folders=self.service.get_template_folders(
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
