from infrastructure.dataverse.telemetry import start_dv_tracking, end_dv_tracking


class DataversePerfMiddleware:
    """
    Middleware liviano que registra conteo y tiempo total de llamadas Dataverse
    por request Django. Solo loggea si se superan umbrales (ver telemetry.py).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_dv_tracking()
        response = self.get_response(request)
        end_dv_tracking(request.path)
        return response
