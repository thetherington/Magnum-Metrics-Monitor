import socket
import json
import argparse
import select
import random
import re


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

        else:

            import api_status
            import importlib

            importlib.reload(api_status)

            metric_results = api_status.returnset(self.substituted)

        collection = {}

        if metric_results:

            for hostID, hostCollection in metric_results.items():

                hostname = hostCollection["hostname"]

                collection = {hostname: {"metrics": []}}

                for metric in hostCollection["health_metrics"]:

                    label = metric[0]

                    match_terms = {
                        "CPU": {"term": "CPU Usage:"},
                        "Memory": {"term": "System Memory:"},
                        "Swap": {"term": "Swap Memory:"},
                    }

                    for term, params in match_terms.items():

                        if params["term"] in label[: len(params["term"])]:

                            func = "self.{}(metric)".format(term)

                            results = eval(func)

                            if isinstance(results, dict):

                                collection[hostname]["metrics"].append(results)

                print(json.dumps(collection, indent=1))

    def CPU(self, metrics):

        label, value, metric_status = metrics
        error = None

        # match the metric label from 'CPU Usage: CPU 15 (%)'
        labelPattern = re.compile(r".+:\s(.*)\s\(.*\)")
        matchLabel = labelPattern.finditer(label)

        for match in matchLabel:

            metric_group = "core" if "CPU" in match.group(1) else "overall"
            metric_label = match.group(1)

            # try to get the converted value in one go by split -> first slice -> decimal % - > round by 4 points
            try:
                metric_value = round(float(value.split("%")[0]) / 100, 4)

            except Exception as e:
                error = str(e)

            metric_collection = {
                "s_group": metric_group,
                "s_metricset": "cpu",
                "s_label": metric_label,
                "s_status": metric_status,
                "s_type": "percentage",
            }

            # update the collection with exception error, otherwise put in the converted value
            if error:
                metric_collection.update({"s_error": error})

            else:
                metric_collection.update({"d_value": metric_value})

            return metric_collection

        # did not match regex right
        return None

    def Memory(self, metrics):

        label, value, metric_status = metrics
        error = None

        # match the metric label from 'System Memory: Inactive'
        labelPattern = re.compile(r".+:\s(.*)")
        matchLabel = labelPattern.finditer(label)

        for match in matchLabel:

            metric_label = match.group(1)

            if "(%)" in metric_label:

                metric_type = "percentage"
                metric_label = metric_label.replace(" (%)", "_pct")

                # try to get the converted value in one go by split -> first slice -> decimal % - > round by 4 points
                try:
                    metric_value = round(float(value.split("%")[0]) / 100, 4)

                except Exception as e:
                    error = str(e)

            else:

                metric_type = "bytes"

                try:

                    unit = value[-1]
                    value = value.split(unit)[0]

                    byte_convert = {
                        "B": 1,
                        "K": 1000,
                        "M": 1000000,
                        "G": 1000000000,
                        "T": 1000000000000,
                    }

                    metric_value = int(float(value) * byte_convert[unit])

                except Exception as e:
                    error = str(e)

            metric_collection = {
                "s_metricset": "memory",
                "s_label": metric_label,
                "s_status": metric_status,
                "s_type": metric_type,
            }

            # update the collection with exception error, otherwise put in the converted value
            if error:
                metric_collection.update({"s_error": error})

            else:

                if metric_type == "bytes":

                    metric_collection.update({"l_value": metric_value})

                else:

                    metric_collection.update({"d_value": metric_value})

            return metric_collection

        # did not match regex right
        return None


    def Swap(self, metrics):

        # just use the Memory function since the data is the same format
        collection = self.Memory(metrics)

        # fix the metricset value so it's term is swap instead of memory
        if isinstance(collection, dict):
            collection.update({"s_metricset": "swap"})

        return collection


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
        "address": "10.9.1.31",
        #'subdata': 'client_trusty_status',
        "verbose": True,
    }

    monitor = metricsMonitor(**params)

    monitor.collect_metrics()

    # if args.pretty:
    #     pass
    # for host, items in monitor.collect_status().items():
    #     print(host)

    #     for name, descr, state in (items['resources']):
    #         print(name, descr, state)

    # if args.dump:
    #     pass
    # print(monitor.collect_status())

    monitor.rpc_close()


if __name__ == "__main__":

    main()
