from prometheus_client import start_http_server

def metrics_run():
    # порт, на котором Prometheus будет забирать метрики
    start_http_server(8000)