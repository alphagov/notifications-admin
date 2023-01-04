import re
import subprocess
from datetime import datetime


def test_last_review_date():
    statement_file_path = "app/templates/views/accessibility_statement.html"

    # test local changes against main for a full diff of what will be merged
    statement_diff = subprocess.run(
        [f"git diff --exit-code origin/main -- {statement_file_path}"], stdout=subprocess.PIPE, shell=True
    )

    date_format = "%d %B %Y"

    # if statement has changed, test the review date was part of those changes
    if statement_diff.returncode == 1:
        raw_diff = statement_diff.stdout.decode("utf-8")
        today = datetime.now().strftime(date_format)
        with open(statement_file_path, "r") as statement_file:
            contents = statement_file.read()
            current_review_date = re.search((r'"Last updated": "(\d{1,2} [A-Z]{1}[a-z]+ \d{4})"'), contents).group(1)
            next_review_due = re.search((r'"Next review due": "(\d{1,2} [A-Z]{1}[a-z]+ \d{4})"'), contents).group(1)

        # guard against changes that don't need to update the review date
        if current_review_date != today:
            assert '"Last updated": "' in raw_diff

        assert datetime.strptime(next_review_due, date_format) > datetime.strptime(current_review_date, date_format)
