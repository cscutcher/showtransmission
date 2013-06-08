import logging
import urllib2
import json
from urlparse import urlparse

logger = logging.getLogger(__name__)


class TransmissionException(Exception):
    pass


class TransmissionClient(object):
    def __init__(self, url):
        self.url = url
        self.session_id = ""
        self.rpc_version_minimum = 1
        parsed_url = urlparse(self.url)
        self.logger = logger.getChild(parsed_url.netloc)

    def get_session(self):
        return self._request("session-get")

    def get_download_dir(self):
        return self.get_session()["download-dir"]

    def check_connection(self):
        session_info = self.get_session()
        if session_info["rpc-version-minimum"] != self.rpc_version_minimum:
            raise TransmissionException("This version of RPC not supported")

    def add_torrent(self, url, download_dir=None):
        arguments = {"filename": url}
        if download_dir is not None:
            arguments["download-dir"] = download_dir
        try:
            return self._request("torrent-add", arguments)
        except TransmissionException as exception:
            if "duplicate torrent" in exception.response_data["result"]:
                self.logger.warn("Already added torrent '%s'" % (url,))
                return exception.response_data["arguments"]
            else:
                raise exception

    def _request(self, method, arguments=None):
        self.logger.debug("Perfoming request %s" % (method,))
        request_dict = {"method": method}
        if arguments is not None:
            request_dict["arguments"] = arguments

        request_data = json.dumps(request_dict)
        self.logger.debug("Request data: %s" % (request_data,))
        request = urllib2.Request(self.url, request_data)
        request.add_header("Content-Type", "json; charset=UTF-8")
        request.add_header("X-Transmission-Session-Id", self.session_id)

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError as http_error:
            if http_error.code == 409:
                logger.debug("Updating session ids")
                self.session_id = http_error.info()["X-Transmission-Session-Id"]
                return self._request(method, arguments)
            else:
                raise http_error

        response_data = json.load(response)
        self.logger.debug("Response: %s" % (response_data,))
        if response_data["result"] != "success":
            exception = TransmissionException("RPC failure: %s" % (response_data["result"],))
            exception.response_data = response_data
            raise exception
        return response_data["arguments"]
