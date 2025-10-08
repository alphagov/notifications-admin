import re
import subprocess
from datetime import datetime

import pytest


@pytest.mark.skip(reason="[NOTIFYNL] Missing mock in overriden views")
def test_last_review_date():
    statement_file_path = "app/templates/views/accessibility_statement.html"

    # test local changes against main for a full diff of what will be merged
    statement_diff = subprocess.run(
        [f"git diff --unified=0 --exit-code origin/main -- {statement_file_path}"],
        capture_output=True,
        shell=True,
    )

    assert not statement_diff.stderr, (
        "Error comparing the accessiblity_statement.html file to origin/main - "
        "make sure this test is run from a local git checkout"
    )
    date_format = "%d %B %Y"

    # if statement has changed, make sure the review date was part of those changes
    if statement_diff.returncode == 1:
        raw_diff = statement_diff.stdout.decode("utf-8")
        with open(statement_file_path) as statement_file:
            contents = statement_file.read()
            last_content_change_at = datetime.strptime(
                re.search((r'"Last updated": "(\d{1,2} [A-Z]{1}[a-z]+ \d{4})"'), contents).group(1), date_format
            )
            next_review_due = datetime.strptime(
                re.search((r'"Next review due": "(\d{1,2} [A-Z]{1}[a-z]+ \d{4})"'), contents).group(1), date_format
            )
        assert '"Last updated": "' in raw_diff or "Last non-functional changes" in raw_diff, (
            "Ensure the last updated timestamp or the Last non-functional changes timestmap has been modified:"
            + raw_diff
        )

        assert last_content_change_at < datetime.today()
        assert next_review_due > datetime.today()
        assert next_review_due > last_content_change_at
