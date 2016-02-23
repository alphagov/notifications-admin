$(() => GOVUK.modules.start());

$(() => new GOVUK.SelectionButtons('.block-label input, .sms-message-option input'));

$(() => $('.error-message').eq(0).parent('label').next('input').trigger('focus'));
