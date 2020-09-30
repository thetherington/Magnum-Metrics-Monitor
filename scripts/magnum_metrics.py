import socket
import json
import argparse
import select
import random


class metricsMonitor:
    def __init__(self, **kwargs):

        self.endFrame = (b"\x0d" + b"\x0a").decode("utf-8")
        self.rpc_id = random.randint(1, 10)
        self.magnum_port = 12021
        self.verbose = None
        self.systemName = None
        self.substituted = None

        for key, value in kwargs.items():

            if ("address" in key) and (value):
                self.magnum_ip = value

            if ("verbose" in key) and (value):
                self.verbose = True

            if ("systemName" in key) and (value):
                self.systemName = value

            if ("subdata" in key) and (value):
                self.substituted = value

        self.rpc_connect()

    def do_ping(self):

        ping_def = {"id": self.rpcId(), "jsonrpc": "2.0", "method": "ping"}

        ping_payload = json.dumps(ping_def) + self.endFrame

        resp = self.rpc_call(ping_payload)

        try:

            if resp["result"] == "pong":
                return True

        except Exception:
            pass

        return None

    def set_version(self):

        version_def = {
            "id": self.rpcId(),
            "jsonrpc": "2.0",
            "method": "health.api.handshake",
            "params": {"client_supported_versions": [2]},
        }

        version_payload = json.dumps(version_def) + self.endFrame

        resp = self.rpc_call(version_payload)

        try:

            if resp["result"]["server_selected_version"] == 2:
                return True

        except Exception:
            pass

        return None

    def get_metrics(self):

        metrics_def = {"id": self.rpcId(), "jsonrpc": "2.0", "method": "get.health.metrics"}

        metrics_payload = json.dumps(metrics_def) + self.endFrame

        retries = 2
        while retries > 0:

            if self.do_ping():
                if self.set_version():

                    resp = self.rpc_call(metrics_payload)

                    try:

                        if "result" in resp:
                            return resp["result"]

                    except Exception:
                        pass

            self.rpc_close()
            self.rpc_connect()

            retries -= 1

        return None

    def rpc_call(self, msg):
        def empty_socket(sock):
            """remove the data present on the socket"""
            while True:
                inputready, o, e = select.select([sock], [], [], 0)
                if len(inputready) == 0:
                    break
                for s in inputready:
                    if not s.recv(1):
                        return

        try:

            empty_socket(self.sock)
            self.sock.send(msg.encode("utf-8"))

            responselist = []

            while True:

                try:
                    data = self.sock.recv(1024).decode("utf-8")
                except socket.timeout:
                    break
                if not data:
                    break

                responselist.append(data)

                if self.endFrame in data:
                    break

            response = json.loads("".join(responselist))

        except Exception:
            return None

        if self.verbose:
            print("-->", msg.strip("\r\n"))
            print("<--", json.dumps(response)[0:300])

        return response

    def rpc_connect(self):

        try:

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2)
            self.sock.connect((self.magnum_ip, self.magnum_port))

            return True

        except Exception as e:

            if self.verbose:
                print(e)

            self.rpc_close()

        return None

    def rpc_close(self):

        try:

            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

            return True

        except Exception:
            return None

    def rpcId(self):

        self.rpc_id = random.randint(1, 10) if self.rpc_id > 99 else self.rpc_id + 1

        return self.rpc_id

    def collect_metrics(self):

        if not self.substituted:

            metric_results = self.get_metrics()

        # else:

        #     import api_status
        #     import importlib

        #     importlib.reload(api_status)

        #     metric_results = api_status.returnset(self.substituted)


def main():

    parser = argparse.ArgumentParser(
        description="Magnum RPC-JSON API Poller program for system health metrics "
    )

    parser.add_argument(
        "-IP", "--address", metavar="127.0.0.1", required=True, help="Magnum Cluster IP Address"
    )
    parser.add_argument(
        "-z", "--fakeit", metavar="", required=False, help="supplement some fake data"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-p", "--pretty", action="store_true", help="Print something pretty")
    group.add_argument("-d", "--dump", action="store_true", help="Dumps some json")

    params = {
        "address": args.address,
        #'subdata': 'client_trusty_status',
        "verbose": args.dump,
    }

    monitor = metricsMonitor(**params)

    if args.pretty:
        pass
        # for host, items in monitor.collect_status().items():
        #     print(host)

        #     for name, descr, state in (items['resources']):
        #         print(name, descr, state)

    if args.dump:
        pass
        # print(monitor.collect_status())

    monitor.rpc_close()


if __name__ == "__main__":

    main()
