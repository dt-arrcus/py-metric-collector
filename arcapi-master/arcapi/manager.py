from arcapi import handlers
from arcapi import transport
from arcapi.errors import HandlerError
from arcapi.types import Handler

def connect(*args, **kwargs):
    """Main connection handler for local/remote clients

    connect() is the main entry point for all ArcAPI clients.
    When a client invokes this function, a number of arguments
    can be passed which determines the locality of the connection.
    If the 'host' keyword argument is included and it does not
    contain the special value 'localhost', the connection is
    determined to be remote.  Otherwise the connection is local
    and passed to the appropriate handler.

    Args:
        args: Variable number of non-keyword arguments.
        kwargs: Variable number of keyword arguments.
    Returns:
        A session object either from the connect_local or
        connect_remote functions.
    """
    local = False
    if 'host' in kwargs:
        host = kwargs['host']
        if host == 'localhost':
            local = True
    else:
        local = True
    if local:
        return connect_local(*args, **kwargs)
    else:
        return connect_remote(*args, **kwargs)

def connect_local(*args, **kwargs):
    """Local connection handler

    Args:
        args: Variable number of non-keyword arguments.
        kwargs: Variable number of keyword arguments.
    Returns:

    """
    if 'handler' in kwargs:
        handler = kwargs['handler']
        if handler == Handler.CLI:
            session = transport.Local()
            return handlers.CliHandler(session, *args, **kwargs)
        else:
            raise HandlerError('Only CLI handler is supported for local connections')
    else:
        session = transport.Local()
        return handlers.CliHandler(session, *args, **kwargs)

def connect_remote(*args, **kwargs):
    """Remote connection handler

    Args:
        args: Variable number of non-keyword arguments.
        kwargs: Variable number of keyword arguments.
    Returns:

    """
    if 'handler' in kwargs:
        handler = kwargs['handler']
        if handler == Handler.NETCONF:
            raise NotImplementedError('NETCONF handler not currently supported')
        if handler == Handler.RESTCONF:
            raise NotImplementedError('RESTCONF handler not currently supported')
        if handler == Handler.CLI:
            session_args = {}
            if 'password' in kwargs:
                session_args['password'] = kwargs['password']
            if 'hostkey_add' in kwargs:
                session_args['hostkey_add'] = kwargs['hostkey_add']
            session = transport.SSH(
                    hostname=kwargs['host'],
                    port=kwargs['port'],
                    username=kwargs['username'],
                    **session_args
                    )

            return handlers.CliHandler(session, *args, **kwargs)
        raise HandlerError('Handler not implemented')
    else:
        raise HandlerError('Remote connection without handler')
