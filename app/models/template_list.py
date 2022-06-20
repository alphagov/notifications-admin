from werkzeug.utils import cached_property

from app import format_notification_type


class TemplateList():
    """
    Represents a list of all templates and folders for a service,
    with optional filtering by "template_type", and by an ancestor
    template_folder_id i.e. only return templates and folders that
    are somewhere inside the specified folder.

    This is used in several places:

    - On the "Templates" page to show whether a folder is totally
    empty or has other types of template in it.

    - On the "Delete template" page to check whether a folder is
    totally empty before deleting it.

    Subclasses of this class are also used in several places - see
    comments on those classes for more details.
    """

    def __init__(
        self,
        *,
        service,
        template_type='all',
        template_folder_id=None,
    ):
        self.service = service
        self.template_type = template_type
        self.template_folder_id = template_folder_id

    def __iter__(self):
        yield from self.items

    @cached_property
    def items(self):
        return list(self._get_templates_and_folders(
            self.template_folder_id, ancestors=[]
        ))

    @property
    def all_template_folders(self):
        return self.service.all_template_folders

    @property
    def all_templates(self):
        return self.service.all_templates

    def _get_templates_and_folders(self, template_folder_id, ancestors):

        for item in self._get_template_folders(template_folder_id):
            yield TemplateListFolder(
                item,
                folders=self._get_template_folders(item['id']),
                templates=self._get_templates(item['id']),
                ancestors=ancestors,
                service_id=self.service.id,
            )
            for sub_item in self._get_templates_and_folders(
                item['id'], ancestors + [item]
            ):
                yield sub_item

        for item in self._get_templates(template_folder_id):
            yield TemplateListTemplate(
                item,
                ancestors=ancestors,
                service_id=self.service.id,
            )

    def _get_templates(self, template_folder_id):
        if template_folder_id:
            template_folder_id = str(template_folder_id)

        return [
            template for template in self.all_templates
            if (set([self.template_type]) & {'all', template['template_type']})
            and template.get('folder') == template_folder_id
        ]

    def _get_template_folders(self, parent_folder_id):
        if parent_folder_id:
            parent_folder_id = str(parent_folder_id)

        return [
            folder for folder in self.all_template_folders
            if (
                folder['parent_id'] == parent_folder_id
                and self._is_folder_visible(folder['id'])
            )
        ]

    def _is_folder_visible(self, template_folder_id):

        if self.template_type == 'all':
            return True

        if self._get_templates(template_folder_id):
            return True

        if any(
            self._is_folder_visible(child_folder['id'])
            for child_folder in self._get_template_folders(template_folder_id)
        ):
            return True

        return False

    @property
    def as_id_and_name(self):
        return [(item.id, item.name) for item in self]

    @property
    def templates_to_show(self):
        return any(self)


class UserTemplateList(TemplateList):
    """
    Represents a filtered list of templates and folders for a
    service based on which folders the specified user has access
    to. See the comment on "all_template_folders".

    This is used in several places:

    - On the "Templates" page. We render all the templates and
    folders to support JS search, hiding nested items with CSS.

    - On the "Templates" page, we also use "all_template_folders"
    to render the list of folders to move a template to.

    - On the SMS reply-to page. We render all the templates and
    folders to support JS search, hiding nested items with CSS.
    """

    def __init__(self, user, **kwargs):
        self.user = user
        super().__init__(**kwargs)

    @cached_property
    def all_templates(self):
        all_folder_ids = [
            folder['id'] for folder in self.all_template_folders
        ]

        return [
            template for template in self.service.all_templates
            # Check if each template is in a folder the user has
            # access to. If it's not in a folder ("None"), then
            # it's at the top level and all users have access.
            if template['folder'] in (all_folder_ids + [None])
        ]

    @cached_property
    def all_template_folders(self):
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
            if not self.user.has_template_folder_permission(folder, service=self.service):
                continue
            parent = self.service.get_template_folder(folder["parent_id"])
            if self.user.has_template_folder_permission(parent, service=self.service):
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
                        if self.user.has_template_folder_permission(parent, service=self.service):
                            break
                user_folders.append(folder_attrs)
        return user_folders


class ServiceTemplateList(UserTemplateList):
    """
    Represents a list of templates and folders for a service,
    with the service itself returned first in the iterable as
    a "fake" folder - a TemplateListService. As this inherits
    from UserTemplateList, the list of templates and folders
    is filtered based on which folders the specified user has
    access to.

    This is used exclusively by the UserTemplateLists class.
    """

    def __iter__(self):
        template_list_service = TemplateListService(
            self.service,
            templates=self._get_templates(
                template_folder_id=None,
            ),
            folders=self._get_template_folders(
                parent_folder_id=None,
            ),
        )

        yield template_list_service

        yield from self._get_templates_and_folders(
            self.template_folder_id,
            ancestors=[template_list_service]
        )


class UserTemplateLists():
    """
    Represents one or more lists of templates and folders
    for each service a user has access to.

    This is used exclusively on the "Copy template" page.
    """

    def __init__(self, user):
        self.services = sorted(
            user.services,
            key=lambda service: service.name.lower(),
        )
        self.user = user

    def __iter__(self):
        if len(self.services) == 1:
            yield from UserTemplateList(
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
