from flask import render_template, current_app, request
from app.main import main
from app import current_service


@main.route("/services/<service_id>/documents/<document_id>/", methods=['GET'])
def download_document(service_id, document_id):

	download_link = '{}/services/{}/documents/{}?key={}'.format(
		current_app.config['DOCUMENT_DOWNLOAD_API_HOST_NAME'],
		service_id,
		document_id,
		request.args.get('key',0)
	)

	return render_template(
	    'views/document-download/index.html',
	    download_link=download_link,
	    service_name=current_service['name']
	)
