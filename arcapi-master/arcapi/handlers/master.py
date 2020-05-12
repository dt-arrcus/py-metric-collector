from arcapi.types import Mode

class MasterHandler(object):
    def __init__(self):
        self._timeout = 30
        self._mode = Mode.PRIVATE


    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, mode):
        self._mode = mode
