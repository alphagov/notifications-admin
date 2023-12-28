import re
import subprocess
from datetime import datetime


def test_last_review_date():
    statement_file_path = "app/templates/views/accessibility_statement.html"

    # test local changes against main for a full diff of what will be merged
    statement_diff = subprocess.run(
        [f"git diff --unified=0 --exit-code origin/main -- {statement_file_path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )

    date_format = "%d %B %Y"

    # could be 1 either because there was a diff, or because there was an error (eg: not in a git checkout).
    if statement_diff.returncode == 1 and not statement_diff.stderr:
        # if statement has changed, test the review date was part of those changes
        raw_diff = statement_diff.stdout.decode("utf-8")
        with open(statement_file_path, "r") as statement_file:
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
