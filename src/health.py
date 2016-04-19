import fcntl
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import getenv
from socketserver import ThreadingMixIn
from threading import Thread


from kazoo.exceptions import NoNodeError
from zookeeper import get_zookeeper


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(self.server.get_bad_brokers()).encode('utf-8'))


class HealthServer(ThreadingMixIn, HTTPServer, Thread):

    def __init__(self):
        HTTPServer.__init__(self, ('0.0.0.0', int(getenv('HEALTH_SERVER_PORT'))), HealthHandler)
        Thread.__init__(self, target=self.serve_forever)
        self._set_fd_cloexec(self.socket)
        self.zk = get_zookeeper()
        self.daemon = True
        self._fetch_brokers = True
        self._fetch_brokers_time = time.time()
        self._bad_brokers = []

    def _brokers_watcher(self, event):
        self._fetch_brokers = True

    @property
    def fetch_brokers(self):
        return self._fetch_brokers or time.time() > self._fetch_brokers_time

    def _get_brokers(self):
        return self.zk.get_children('/brokers/ids', self._brokers_watcher)

    def _get_bad_brokers(self, good_brokers):
        bad_brokers = set()
        good_brokers = set(map(int, good_brokers))
        for topic in self.zk.get_children('/brokers/topics'):
            try:
                details = json.loads(self.zk.get('/brokers/topics/' + topic)[0].decode('utf-8'))
                for partition, brokers in details['partitions'].items():
                    for broker in brokers:
                        if broker not in good_brokers:
                            bad_brokers.add(broker)
            except NoNodeError:
                pass
        return list(bad_brokers)

    def get_bad_brokers(self):
        if self.fetch_brokers:
            brokers = self._get_brokers()
            self._bad_brokers = self._get_bad_brokers(brokers)
            self._fetch_brokers = False
            self._fetch_brokers_time = time.time() + 60
        return self._bad_brokers

    @staticmethod
    def _set_fd_cloexec(fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        fcntl.fcntl(fd, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
