import rpyc
from rpyc.utils.server import ThreadedServer
from threading import Thread
import time
import collections

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def provide_objects(service_cls, objects, name=None):
    class Service_(service_cls):
        pass
    Service_.objects = objects
    if name is not None:
        Service_.ALIASES = [name]
    return Service_


class Service(rpyc.Service):
    def exposed_get(self, k):
        return self.objects[k]

    def exposed_set(self, k, v):
        self.objects[k] = v

    def exposed_len(self):
        return len(self.objects)

    def exposed_keys(self):
        return self.objects.keys()

    def exposes_values(self):
        return self.objects.values()


def launch_server(server):
    logger.info("Serving...")
    server.start()
    logger.info("Finishing")


def launch_thread(func, *args, **kwargs):
    class Thread_(Thread):
        def run(self):
            func(*args, **kwargs)
    t = Thread_()
    t.daemon = True
    t.start()


class Controller(object):

    def __init__(self):
        self.paused = False

    def exposed_pause(self):
        self.paused = True

    def handle(self):
        was_pausing = False
        if self.paused is True:
            logger.info("pausing...")
            was_pausing = True
        while self.paused is True:
            time.sleep(1)
        if was_pausing is True:
            logger.info("resuming")

    def exposed_resume(self):
        self.paused = False


def launch(objects, host="0.0.0.0", port=12345, name="unnamed",
           server_cls=ThreadedServer,
           server_kwargs=None):
    service = provide_objects(Service, objects, name=name)
    if server_kwargs is None:
        server_kwargs = dict()
    server = server_cls(service=service,
                        auto_register=True,
                        hostname=host,
                        port=port,
                        **server_kwargs)
    launch_thread(launch_server, server)


def connect(host="0.0.0.0", port=12345, **kwargs):
    conn = rpyc.connect(host, port=port, **kwargs)
    return ConnectionWrapper(conn)


class ConnectionWrapper(collections.Mapping):

    def __init__(self, conn):
        self._conn = conn

    def __set__(self, k, v):
        self._conn.root.set(k, v)

    def __iter__(self):
        return iter(self._conn.root.keys())

    def __len__(self):
        return len(self._conn.root.len())

    def __getitem__(self, key):
        return self._conn.root.get(key)

    def __setitem__(self, key, value):
        self._conn.root.set(key, value)

    def __getattr__(self, k):
        if k.startswith("_"):
            return self.__dict__[k]
        return self[k]

    def __setattr__(self, k, v):
        if k.startswith("_"):
            self.__dict__[k] = v
        else:
            self[k] = v

if __name__ == "__main__":
    controller = Controller()
    params = dict(
            learning_rate=0.1,
            controller=controller
    )
    launch(params, name="hp")
    for i in range(100):
        print("iteration {}".format(i))
        time.sleep(5)
        controller.handle()
