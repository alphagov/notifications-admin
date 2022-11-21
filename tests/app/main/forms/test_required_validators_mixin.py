from flask_wtf import FlaskForm as Form
from wtforms import Field

from app.main.forms import RequiredValidatorsMixin


def test_required_validators_mixin_(client_request, mocker):
    validator_1 = mocker.Mock(field_flags={})
    validator_2 = mocker.Mock(field_flags={})
    validator_3 = mocker.Mock(field_flags={})

    class MyField(RequiredValidatorsMixin, Field):
        required_validators = [validator_1]

    class MyForm(Form):
        my_field = MyField(validators=[validator_2])

    form_1 = MyForm()
    form_2 = MyForm()
    # this still overwrites required_validators entirely
    form_2.my_field.validators = [validator_3]

    assert form_1.my_field.validators == [validator_1, validator_2]
    assert form_2.my_field.validators == [validator_3]
