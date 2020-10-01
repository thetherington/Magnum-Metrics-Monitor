import json
from insite_plugin import InsitePlugin
from magnum_metrics import metricsMonitor


class Plugin(InsitePlugin):
    def can_group(self):
        return False

    def fetch(self, hosts):

        host = hosts[-1]

        try:

            self.monitor

        except Exception:

            params = {"address": host}

            self.monitor = metricsMonitor(**params)

        documents = []

        collection, collection_group = self.monitor.collect_metrics()

        if collection and collection_group:

            for server, metrics in collection_group.items():

                for metric in self.monitor.list_metrics(metrics):

                    document = {"fields": metric, "host": server, "name": "groups"}

                    documents.append(document)

            for server, parts in collection.items():

                for metric in parts["metrics"]:

                    document = {"fields": metric, "host": server, "name": "metrics"}

                    documents.append(document)

        return json.dumps(documents)

    def dispose(self):

        try:

            self.monitor.rpc_close()

        except Exception:
            pass
