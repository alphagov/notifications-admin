import hashlib

from flask import current_app


class AssetFingerprinter:
    """
    Get a unique hash for an asset file, so that it doesn't stay cached
    when it changes

    Usage:

        in the application
        template_data.asset_fingerprinter = AssetFingerprinter()

        where template data is how you pass variables to every template.

        in template.html:
        {{ asset_fingerprinter.get_url('stylesheets/application.css') }}

    * 'app/static' is assumed to be the root for all asset files
    """

    def __init__(self, filesystem_path="app/static/"):
        self._cache = {}
        self._filesystem_path = filesystem_path

    def get_url(self, asset_path, with_querystring_hash=True):
        # you can't get a URL without being in the app context
        _asset_root = current_app.config["ASSET_ROOT"]

        if not with_querystring_hash:
            return _asset_root + asset_path
        if asset_path not in self._cache:
            self._cache[asset_path] = (
                _asset_root + asset_path + "?" + self.get_asset_fingerprint(self._filesystem_path + asset_path)
            )
        return self._cache[asset_path]

    def get_asset_fingerprint(self, asset_file_path):
        return hashlib.md5(self.get_asset_file_contents(asset_file_path)).hexdigest()

    def get_asset_file_contents(self, asset_file_path):
        with open(asset_file_path, "rb") as asset_file:
            contents = asset_file.read()
        return contents


asset_fingerprinter = AssetFingerprinter()
