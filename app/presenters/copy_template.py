from app.models.template_list import TemplateListFolder, UserTemplateList


class CopyTemplate:
    """
    Represents one or more lists of templates and folders
    for each service a user has access to.
    """
    def __init__(
        self,
        user,
        template_folder_id=None,
        service=None,
    ):
        self.service = service
        self.user = user
        self.template_folder_id = template_folder_id

    @property
    def template_folder_path(self):
        return self.service.get_template_folder_path(self.template_folder_id)

    @property
    def items(self):
        if self.service:
            yield from UserTemplateList(
                service=self.service,
                user=self.user,
                template_folder_id=self.template_folder_id
            )
            return

        services = sorted(
            self.user.services,
            key=lambda service: service.name.lower(),
        )

        if len(services) == 1:
            yield from UserTemplateList(
                service=services[0],
                user=self.user,
            )
            return

        for service in services:
            yield from _ServiceTemplateList(
                service=service,
                user=self.user,
            )

    @property
    def templates_to_show(self):
        return bool(self.user.services)


class _ServiceTemplateList(UserTemplateList):
    """
    Represents a list of templates and folders for a service,
    with the service itself returned first in the iterable as
    a "fake" folder - a TemplateListService. As this inherits
    from UserTemplateList, the list of templates and folders
    is filtered based on which folders the specified user has
    access to.
    """

    def __iter__(self):
        template_list_service = _TemplateListService(
            self.service,
            templates=self._get_templates(
                template_type='all',
                template_folder_id=None,
            ),
            folders=self._get_template_folders(
                template_type='all',
                parent_folder_id=None,
            ),
        )

        yield template_list_service

        yield from self._get_templates_and_folders(
            self.template_type,
            self.template_folder_id,
            ancestors=[template_list_service]
        )


class _TemplateListService(TemplateListFolder):
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
