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

        # for hostname, items in self.monitor.collect_metrics().items():

        # for name, descr, state in items['resources']:

        #     fields = {
        #         'hostname': hostname,
        #         'name': name,
        #         'description': descr,
        #         'state': state
        #     }

        #     document = {
        #         'fields': fields,
        #         'host': host,
        #         'name': 'metrics_monitor'
        #     }

        #     documents.append(document)

        return json.dumps(documents)

    def dispose(self):

        try:

            self.monitor.rpc_close()

        except Exception:
            pass
