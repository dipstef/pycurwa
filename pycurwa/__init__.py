from httpy.client.requests import HttpRequests


class PyCurwa(HttpRequests):

    def execute(self, request, **kwargs):
        return super(PyCurwa, self).execute(request, **kwargs)