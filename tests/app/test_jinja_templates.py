from itertools import chain
from pathlib import Path

import pytest
from flask import current_app
from jinja2.nodes import Call, FromImport, Name
from orderedset import OrderedSet


class UnusedJinjaImports(Exception):
    def __init__(self, unused_imports, file):
        separator = "\n  • "
        formatted_unused_imports = separator.join(unused_imports)
        super().__init__(f"\n\nUnused Jinja imports:{separator}{formatted_unused_imports}\n\nFound in {file}")


templates_dir = Path(__file__).parent.parent.parent.resolve() / "app/templates"
files = sorted(templates_dir.glob("**/*.html"))


@pytest.mark.parametrize("file", files, ids=[str(path.relative_to(templates_dir)) for path in files])
def test_for_unused_jinja_imports(client_request, file):
    parse_tree = current_app.jinja_env.parse(file.read_text())

    calls = set(node.node.name for node in parse_tree.find_all(Call) if isinstance(node.node, Name))
    imports = OrderedSet(chain.from_iterable(node.names for node in parse_tree.find_all(FromImport)))

    if unused_imports := imports - calls:
        raise UnusedJinjaImports(unused_imports, file)
