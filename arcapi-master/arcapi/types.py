class Handler(object):
    CLI = 0
    NETCONF = 1
    RESTCONF = 2

class Encoding(object):
    TEXT = None
    XML = 'xml'
    JSON = 'json'

class LoadOperation(object):
    FEED = None
    MERGE = 'merge'
    OVERRIDE = 'override'
    REPLACE = 'replace'

class Mode(object):
    EXCLUSIVE = 'exclusive'
    SHARED = 'shared'
    PRIVATE = 'terminal'

class Reply(object):
    def __init__(self, error=None, message=''):
        self._error = error
        self._message = message

    @property
    def error(self):
        """Getter for the error field

        Retrieve the error field of the Reply() object.

        Returns:
            A string representing the error value if set,
            otherwise return None.
        """
        if self._error:
            return self._error
        else:
            return None

    @error.setter
    def error(self, error):
        """Setter for the error field

        Set the error field in a Reply() object.

        Args:
            error: A string value of an error value as defined
                in errors.py.
        """
        self._error = error

    @property
    def message(self):
        """Getter for the message field

        Retrieve the message field of the Reply() object.

        Returns:
            A string representing the message value.
        """
        return self._message

    @message.setter
    def message(self, message):
        """Setter for the message field

        Set the message field in a Reply() object.

        Args:
            message: A string value of a message value.
        """
        self._message = message
