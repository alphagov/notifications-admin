import pytest
from freezegun import freeze_time

from app.models.user import User
from app.utils.login import email_needs_revalidating


@freeze_time('2020-11-27T12:00:00')
@pytest.mark.parametrize(('email_access_validated_at', 'expected_result'), (
    ('2020-10-01T11:35:21.726132Z', False),
    ('2020-07-23T11:35:21.726132Z', True),
))
def test_email_needs_revalidating(
    api_user_active,
    email_access_validated_at,
    expected_result,
):
    api_user_active['email_access_validated_at'] = email_access_validated_at
    assert email_needs_revalidating(User(api_user_active)) == expected_result
