from flask import jsonify, request
from app import (version, status_api_client)
from app.status import status
from notifications_python_client import HTTPError


@status.route('/_status', methods=['GET'])
def show_status():
    if request.args.get('elb', None):
        return jsonify(status="ok"), 200
    else:
        try:
            api_status = status_api_client.get_status()
        except HTTPError as e:
            return jsonify(status="error", message=str(e.message)), 500
        return jsonify(
            status="ok",
            api=api_status,
            travis_commit=version.__travis_commit__,
            travis_build_number=version.__travis_job_number__,
            build_time=version.__time__), 200
