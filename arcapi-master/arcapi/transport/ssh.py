import paramiko

from arcapi.transport.session import Session

class SSH(Session):
    def __init__(self, hostname, port, username, **kwargs):
        self.local = False
        self._hostname = hostname
        self._port = port
        self._username = username
        self._ssh_key_add = False
        self._session = None

        if 'password' in kwargs:
            self._password = kwargs['password']

        if 'hostkey_add' in kwargs:
            if kwargs['hostkey_add']:
                self._ssh_key_add = True

        self._session = self._connect()

    def _connect(self):
        session = paramiko.SSHClient()
        if self._ssh_key_add:
            session.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        session.connect(
                hostname=self._hostname,
                port=self._port,
                username=self._username,
                password=self._password,
                )
        self._session = session
        return session

    def exec_command(self, command):
        return self._session.exec_command(command)

    def invoke_shell(self):
        return self._session.invoke_shell()

    def close(self):
        if self._session:
            self._session.close()
