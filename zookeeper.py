import logging
import os
import random
import requests
import time

from kazoo.client import KazooClient
from kazoo.exceptions import NoNodeError
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class ExhibitorEnsembleProvider:

    TIMEOUT = 3.1

    def __init__(self, hosts, port, uri_path='/exhibitor/v1/cluster/list', poll_interval=300):
        self._exhibitor_port = port
        self._uri_path = uri_path
        self._poll_interval = poll_interval
        self._exhibitors = hosts
        self._master_exhibitors = hosts
        self._zookeeper_hosts = ''
        self._next_poll = None
        while not self.poll():
            logger.info('waiting on exhibitor')
            time.sleep(5)

    def poll(self):
        if self._next_poll and self._next_poll > time.time():
            return False

        json = self._query_exhibitors(self._exhibitors)
        if not json:
            json = self._query_exhibitors(self._master_exhibitors)

        if isinstance(json, dict) and 'servers' in json and 'port' in json:
            self._next_poll = time.time() + self._poll_interval
            zookeeper_hosts = ','.join([h + ':' + str(json['port']) for h in sorted(json['servers'])])
            if self._zookeeper_hosts != zookeeper_hosts:
                logger.info('ZooKeeper connection string has changed: %s => %s', self._zookeeper_hosts, zookeeper_hosts)
                self._zookeeper_hosts = zookeeper_hosts
                self._exhibitors = json['servers']
                return True
        return False

    def _query_exhibitors(self, exhibitors):
        random.shuffle(exhibitors)
        for host in exhibitors:
            uri = 'http://{}:{}{}'.format(host, self._exhibitor_port, self._uri_path)
            try:
                response = requests.get(uri, timeout=self.TIMEOUT)
                return response.json()
            except RequestException:
                pass
        return None

    @property
    def zookeeper_hosts(self):
        return self._zookeeper_hosts


class Exhibitor:

    def __init__(self, exhibitor, chroot):
        self.chroot = chroot
        self.exhibitor = ExhibitorEnsembleProvider(exhibitor['hosts'], exhibitor['port'], poll_interval=30)
        self.client = KazooClient(hosts=self.exhibitor.zookeeper_hosts + self.chroot,
                                  command_retry={
                                      'deadline': 10,
                                      'max_delay': 1,
                                      'max_tries': -1},
                                  connection_retry={'max_delay': 1, 'max_tries': -1})
        self.client.add_listener(self.session_listener)
        self.client.start()

    def session_listener(self, state):
        pass

    def _poll_exhibitor(self):
        if self.exhibitor.poll():
            self.client.set_hosts(self.exhibitor.zookeeper_hosts)

    def get(self, *params):
        self._poll_exhibitor()
        return self.client.retry(self.client.get, *params)

    def get_children(self, *params):
        self._poll_exhibitor()
        try:
            return self.client.retry(self.client.get_children, *params)
        except NoNodeError:
            return []


def get_zookeeper():
    return Exhibitor({'hosts': [os.getenv('EXHIBITOR_HOST')], 'port': 8181}, os.getenv('ZOOKEEPER_PREFIX'))
