from flask import redirect

from app.main import main


@main.route('/.well-known/security.txt', methods=['GET'])
@main.route('/security.txt', methods=['GET'])
def security_policy():
    # See GDS Way security policy which this implements
    # https://gds-way.cloudapps.digital/standards/vulnerability-disclosure.html#vulnerability-disclosure-and-security-txt
    return redirect("https://vdp.cabinetoffice.gov.uk/.well-known/security.txt")
