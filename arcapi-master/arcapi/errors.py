from arcapi import ArcAPIError

errors = {
        1: 'SHELL_ERROR',
        2: 'INVALID_COMMAND',
        3: 'COMMIT_NO_MODIFICATIONS',
        4: 'OPERATION_ABORTED',
        5: 'OPERATION_ERROR',
        6: 'PROCESS_UNAVAILABLE',
        7: 'PROCESS_TIMEOUT',
        8: 'UNSUPPORTED_ENCODING',
}

class ConnectError(ArcAPIError):
    pass

class HandlerError(ArcAPIError):
    pass

class ContextError(ArcAPIError):
    pass

def name(value):
    """Return error value given an identifier

    Given an error identifier defined in the errors{}
    dict, return the corresponding error string value.

    Args:
        value: Integer representing an error identifier.
    Returns:
        A string representing an error value.
    """
    return errors[value]

class Error(object):
    SHELL_ERROR = 1
    INVALID_COMMAND = 2
    COMMIT_NO_MODIFICATIONS = 3
    OPERATION_ABORTED = 4
    OPERATION_ERROR = 5
    PROCESS_UNAVAILABLE = 6
    PROCESS_TIMEOUT = 7
    UNSUPPORTED_ENCODING = 8
