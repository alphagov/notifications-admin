from flask import jsonify

from flask import request

from app import version

from app.status import status

@status.route('/_status', methods=['GET'])
def show_status():
    if request.args.get('elb', None):
        return jsonify(status="ok"), 200
    else:
        return jsonify(
            status="ok",
            travis_commit=version.__travis_commit__,
            travis_build_number=version.__travis_job_number__,
            build_time=version.__time__), 200
