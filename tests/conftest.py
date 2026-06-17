# -*- coding: utf-8 -*-
#  Copyright 2011 Takeshi KOMIYA
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import http.server
import os
import sys
import threading
import urllib.parse
import urllib.request

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

# Real fixture files served over HTTP, one per image type referenced by the
# test diagrams (node_icon.diag, background_url_image.diag, ...).
REMOTE_FIXTURES = {
    '.ico': 'favicon.ico',
    '.gif': 'sample.gif',
    '.svg': 'sample.svg',
    '.eps': 'sample.eps',
}
DEFAULT_FIXTURE = 'sample.gif'


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FIXTURES_DIR, **kwargs)

    def log_message(self, *args):
        pass


@pytest.fixture(scope='session')
def image_server():
    """Serve the per-format image fixtures over real HTTP on localhost."""
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield 'http://%s:%d' % (host, port)
    finally:
        server.shutdown()


@pytest.fixture(autouse=True)
def redirect_remote_images(monkeypatch, image_server):
    """Redirect remote image URLs to the local server.

    Test diagrams reference images by ``http(s)`` URL (e.g.
    http://blockdiag.com/favicon.ico). Hitting the internet makes the suite
    flaky and fails outright when a host is unreachable. We keep the real
    network code path (``isurl`` -> ``urlopen`` -> per-format decoding) but
    point every request at a local server that serves a real file of the same
    type, so ico/gif/svg/eps over HTTP are still exercised offline.
    """
    real_urlopen = urllib.request.urlopen

    def fake_urlopen(url, *args, **kwargs):
        target = url.full_url if hasattr(url, 'full_url') else url
        ext = os.path.splitext(urllib.parse.urlparse(target).path)[1].lower()
        name = REMOTE_FIXTURES.get(ext, DEFAULT_FIXTURE)
        return real_urlopen('%s/%s' % (image_server, name), *args, **kwargs)

    monkeypatch.setattr(urllib.request, 'urlopen', fake_urlopen)
    yield
