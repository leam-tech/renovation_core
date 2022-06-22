import renovation


class ReportError(Exception):
    http_status_code = 500
    message = renovation._("Error with Report")
    error_code = "UNKNOWN_REPORT_ERROR"
    data = None

    def __init__(self):
        self.data = renovation._dict()


class NotFound(ReportError):
    def __init__(self, report: str):
        self.http_status_code = 404
        self.message = renovation._("Report {0} cannot be found").format(report)
        self.error_code = "NOT_FOUND"
        self.data = renovation._dict(report=report)


class PermissionError(ReportError):
    def __init__(self, report: str):
        self.http_status_code = 403
        self.message = renovation._("Permission Denied for Report: {0}").format(report)
        self.error_code = "PERMISSION_DENIED"
        self.data = renovation._dict(report=report)


class ReportDisabled(ReportError):
    def __init__(self, report: str):
        self.http_status_code = 400
        self.message = renovation._("Disabled Report: {0}").format(report)
        self.error_code = "REPORT_DISABLED"
        self.data = renovation._dict(report=report)
