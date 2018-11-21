class TemplateList():

    def __init__(
        self,
        service,
        template_type='all',
        template_folder_id=None,
    ):
        self.service = service
        self.template_type = template_type
        self.template_folder_id = template_folder_id

    def __iter__(self):
        for item in self.get_templates_and_folders(
            self.template_type, self.template_folder_id, ancestors=[]
        ):
            yield item

    def get_templates_and_folders(self, template_type, template_folder_id, ancestors):

        for item in self.service.get_template_folders(
            template_type, template_folder_id
        ):
            yield TemplateListFolder(
                item,
                folders=self.service.get_template_folders(
                    self.template_type, item['id']
                ),
                templates=self.service.get_templates(
                    self.template_type, item['id']
                ),
                ancestors=ancestors,
            )
            for sub_item in self.get_templates_and_folders(
                template_type, item['id'], ancestors + [item]
            ):
                yield sub_item

        for item in self.service.get_templates(
            self.template_type, template_folder_id
        ):
            yield TemplateListTemplate(
                item,
                ancestors=ancestors,
            )

    @property
    def templates_to_show(self):
        return any(self)

    @property
    def folder_is_empty(self):
        return not any(self.get_templates_and_folders(
            'all', self.template_folder_id, []
        ))


class TemplateListItem():

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
    ):
        super().__init__(template, ancestors)
        self.hint = {
            'email': 'Email template',
            'sms': 'Text message template',
            'letter': 'Letter template',
        }.get(template['template_type'])


class TemplateListFolder(TemplateListItem):

    is_folder = True

    def __init__(
        self,
        folder,
        templates,
        folders,
        ancestors,
    ):
        super().__init__(folder, ancestors)
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
