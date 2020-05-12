from __future__ import unicode_literals

import datetime
import json
import pexpect
import os
import re
import stat
import subprocess
import tempfile
import time

from select import select
from getpass import getuser

from arcapi.errors import ContextError
from arcapi.errors import Error
from arcapi.types import Encoding
from arcapi.types import Reply
from arcapi.handlers.master import MasterHandler

CONFD_CLI = '/usr/bin/confd_cli'

RECV_BUFFER = 5000
def run_cmdfile(cmdfile):
    """Process a non-interactive command file through confd_cli

    For non-interactive sessions that do not use expect to
    interact from within the context of arcos_cli, pipe commands
    that are contained within a file through confd_cli directly
    from within an underlying shell context.

    Args:
        cmdfile: A string representing a local filename
    Returns:
        A tuple containing the process return code in addition
        to the raw output from the commands executed from within
        the cmdfile.
    """
    current_user = getuser()
    os.chmod(cmdfile, stat.S_IROTH | stat.S_IRUSR)
    command_file = open(cmdfile)

    process = subprocess.Popen([CONFD_CLI, '-s', '-u', current_user],
            stdin=command_file, stdout=subprocess.PIPE)
    output = process.communicate()[0]
    command_file.close()
    return (process.returncode, output)

class CliHandler(MasterHandler):
    def __init__(self, session, *args, **kwargs):
        super(CliHandler, self).__init__()
        self.session = session
        self.child = None
        self.shell_prompt = r'($|#)'
        self.oper_prompt = r'ARCAPI_OPER\#\ '
        self.conf_prompt = r'ARCAPI_CONF\#\ '

        if self.session.local is True:
            self.arcos_shell = False
        else:
            self.chan = self.session.invoke_shell()
            self.arcos_shell = self._arcos_shell()

    def _arcos_shell(self):
        """Determine the ArcAPI shell environment

        For remote/local users, determine the initial shell context
        of a given ArcAPI session.

        Returns:
            (boolean): Return True if the executing context is within
            the ArcOS CLI.  If the executing context is an underlying
            shell (e.g. bash), return False
        """
        self._send_command('id')
        buf = self._wait(self.shell_prompt)
        if 'uid=' in buf:
            return False
        else:
            return True


    def _send_command(self, command):
        """Send a command on a pre-established remote channel

        Wrapper function to send a command along with a carriage
        return on a pre-established remote channel.

        Args:
            command: A string representing a single operational or
                configuration mode command.
        """
        self.chan.send(command)
        self.chan.send('\n')

    def _wait(self, prompt):
        """Wait for a specified prompt to be returned

        Wrapper function for expect-like based interaction to return
        after the specified prompt has been matched.

        Args:
            prompt: A string representing a match prompt
        Returns:
            If there is a match on the input prompt, the buffer is
            considered drained.  In this case, the buffer is returned
            as a string directly to the caller.  Should the match not
            succeed and the timeout threshold is hit, a Reply() object
            is returned as a PROCESS_TIMEOUT to the caller.
        """
        ## Wait just enough to let remote start writing into the
        ## channel
        time.sleep(0.1)
        buf = ''
        drained = False
        timeout = datetime.datetime.now() + datetime.timedelta(
                seconds=self.timeout)
        while timeout > datetime.datetime.now():
            rd, wr, err = select([self.chan], [], [], 0.1)
            if rd:
                recv = self.chan.recv(RECV_BUFFER)
                if isinstance(recv, bytes):
                    recv = recv.decode('utf-8', 'replace')
                buf += recv
                if prompt is not None and re.search(r'{}\s?$'.format(
                        prompt), recv):
                    drained = True
                    break
        if drained:
            return buf
        else:
            return Reply(Error.PROCESS_TIMEOUT,
                    'Remote command timed out')

    def _cleanse_buffer(self, buf, pre='\n', post='\n'):
        """Message preprocessor to cleanse buffer contents

        When buffer results are marshaled back to the caller within
        a Reply() object message field, this function is utilized
        to search for the correct portion of the message and remove
        line breaks before returning to the caller.

        Args:
            buf: A string representing the message to be cleansed
            pre: A string representing the first match condition
            post: A string representing the last match condition
        Returns:
            A string representing the contents of buf within the
            pre and post match conditions with line breaks removed.
        """
        buf = buf[buf.find(pre):]
        buf = buf[:buf.rfind(post)]
        if 'Aborted' in buf:
            buf = buf[buf.find('Aborted'):].strip()
        if 'Error' in buf:
            buf = buf[buf.find('Error'):].strip()
        if 'Subsystem started' in buf:
            buf = buf[buf.find('Subsystem started'):].strip()
        if 'stop on error' in buf:
            buf = buf[buf.find('stop on error'):].strip()
        return buf

    def _validate_buffer(self, command, buf):
        """Validate the contents of command responses

        Given an input buffer message as a response to a previously
        sent command, validate the contents of the message and pack
        an appropriate error and message within a Reply() object.

        Args:
            command: A string representing the command issued
            buf: A string representing the return buffer
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        error = None
        message = ''

        if '----^' in buf:
            message = 'Syntax Error: [{}]'.format(command.strip())
            error = Error.INVALID_COMMAND
        elif 'Commit complete' in buf:
            message = 'Commit Successful'
        elif 'No modifications to commit' in buf:
            message = 'No modifications to commit'
            error = Error.COMMIT_NO_MODIFICATIONS
        elif 'Aborted' in buf:
            message = '{} [{}]'.format(self._cleanse_buffer(buf), command)
            error = Error.OPERATION_ABORTED
        elif 'Error' in buf:
            message = '{}'.format(self._cleanse_buffer(buf))
            error = Error.OPERATION_ERROR
        elif 'Subsystem started' in buf:
            message = '{}'.format(self._cleanse_buffer(buf))
            error = Error.OPERATION_ERROR
        elif 'Validation complete' in buf:
            message = 'Validation Successful'
        else:
            message = buf

        response = Reply()
        response.error = error
        response.message = message
        return response

    def _commit_handler(self, commands):
        """Process command sequence as commit transaction

        Given a list of commands, this handler is invoked should
        the command list contain a 'commit' element.  Special
        handling is necessary in order to deal with potential
        transaction delays.

        Args:
            commands: A list of commands to be processed in
                sequence for a commit operation.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        response = Reply()

        for command in commands:
            ## Strip any leading whitespace as this will result
            ## in desync of send/recv
            command = command.strip()

            if command == 'end' or command == 'end no-confirm': 
                prompt = self.oper_prompt
            else:
                prompt = self.conf_prompt

            ## Skip processing any lines that end w/ !\n
            if '!\n' in command:
                continue
            if 'commit' in command:
                if self.session.local is True:
                    self.child.sendline(command)
                    (success, check_response) = self._check_expect_response(
                            command, prompt)
                    buf = self.child.before
                    if success:
                        response = self._validate_buffer(command, buf)
                    else:
                        response = check_response
                else:
                    self._send_command(command)
                    ## Arbitrary sleep before commit
                    time.sleep(2)
                    buf = self._wait(prompt)
                    if isinstance(buf, Reply):
                        # command timeout
                        response = buf
                        break
                    response = self._validate_buffer(command, buf)
                ## Need to check if response is good and if not break loop
                if response and response.error is not None:
                    break

            else:
                if self.session.local is True:
                    self.child.sendline(command)
                    (success, check_response) = self._check_expect_response(
                            command, prompt)
                    if not success:
                        ## Breaking from loop to send error back to caller
                        response = check_response
                        break

                    buf = self.child.before
                    if re.search("end$|end no-confirm$", command) is None:
                        response = self._validate_buffer(command, buf)
                        if response.error is not None:
                            break
                    else:
                        self._validate_buffer(command, buf)
                else:
                    self._send_command(command)
                    buf = self._wait(prompt)
                    if isinstance(buf, Reply):
                        response = buf
                    else:
                        if re.search("end$|end no-confirm$", command) is None:
                            response = self._validate_buffer(command, buf)
                        else:
                            self._validate_buffer(command, buf)
                    if response.error is not None:
                        break

        return response

    def _check_expect_response(self, command, match, timeout=None, 
        close_child=True):
        """Check a command response against a match string

        Alternative function to _wait which uses expect to match
        an argument against the return buffer as a result of a
        previous sendline.

        Args:
            command: A string representing the command previously
                sent that corresponds to the buffer returned.
            match: A string indicating a word to match in the
                buffer response.
            timeout: A integer respresenting the time pexpect waits for
                command to return.  If the caller doesn't set this value
                the timeout value will be equal to the object level timeout
            close_child: Boolean value that instructs if the child
                should be terminated
        Returns:
            A tuple indicating success (True) or failure (False)
            along with a Reply() object.  If the reply is successful,
            the appropriate data payload is returned in the message
            field.  If the reply is a failure, an appropriate error
            code is set along with a message description indicating
            the failure.
        """
        response = Reply()
        timeout = self.timeout if timeout is None else timeout
        try:
            self.child.expect(match, timeout)
            return(True, None)
        except pexpect.EOF:
            # we caught a pexpect.EOF
            response.error = Error.PROCESS_UNAVAILABLE
            response.message = 'Management daemon not available'
            if close_child:
                if self.child.isalive():
                    self.child.close(force=True)
            return(False, response)
       
        except pexpect.TIMEOUT:
            # we caught a pexpect.TIMEOUT
            response.error = Error.PROCESS_TIMEOUT
            response.message = 'Command [{}] timed out.'.format(command)
            if close_child:
                if self.child.isalive():
                    self.child.close(force=True)
            return (False, response)
       

    def _noninteractive_command(self, commands, **kwargs):
        """Execute a set of noninteractive CLI commands

        Internal only API that is front-ended by all public facing
        APIs.  This code path is executed for configuration or
        operational commands should the context of the user session
        be outside of the ArcOS CLI.

        Non-interactive commands are written to a temporary file and
        piped directly into the ArcOS CLI shell vs. an interactive
        expect based mechanism.

        Args:
            commands: A list of commands to be executed.
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        response = Reply()

        # will handle delete outside the scope of tempfile
        tf = tempfile.NamedTemporaryFile(delete=False)
        for command in commands:
            tf.write('{}\n'.format(command))
        tf.flush()
        tf.close()
        try:
            command_status = run_cmdfile(tf.name)
            os.remove(tf.name)
        except subprocess.CalledProcessError as e:

            respone.error = Error.OPERATION_ERROR
            response.message = json.dumps({'rc': 255,
                                           'message': command_status[1]})
            os.remove(tf.name)
            return response

        # returncode non-zero
        if command_status[0] != 0:
            # spawning confd_cli with -s so when a command/commit/validate fails
            # it should return a non-zero exit code
            val_buf = self._validate_buffer('', command_status[1])
            response.error = val_buf.error
            response.message = json.dumps({'rc': command_status[0],
                                           'message': val_buf.message})
            return response
        else:
            # should only hit this when a valid command is sent through
            val_buf = self._validate_buffer('', command_status[1])
            response.error = val_buf.error
            response.message = json.dumps({'rc': command_status[0],
                                           'message': val_buf.message})

            return response

    def _interactive_command(self, commands, **kwargs):
        """Execute a set of interactive CLI commands

        Internal only API that is front-ended by all public facing
        APIs.  This code path is executed for configuration or
        operational commands should the context of the user session
        be within the ArcOS CLI.

        Args:
            commands: A list of commands to be executed.
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        response = Reply()

        if 'timeout' in kwargs:
            self.timeout = kwargs['timeout']

        if 'cli' in kwargs:
            if kwargs['cli'] is not None:
                command = 'arcos_cli'
                if self.session.local is True:
                    self.child = pexpect.spawnu(command)
                    self.arcos_shell = True
                else:
                    self._send_command(command)
                    self._wait(self.shell_prompt)
                    self.arcos_shell = True

        if 'shell' in kwargs:
            if kwargs['shell']:
                commands = ['bash ' + command for command in commands]
                self.arcos_shell = True

        if self.arcos_shell:
            prompts = {
                'prompt1': self.oper_prompt,
                'prompt2': self.conf_prompt
            }
            if self.session.local is True:
                retry = 0
                for prompt in prompts:
                    success = False
                    retry = 0
                    ## adding a retry to deal with odd timing issues after arcos_cli
                    ## is initially spawned
                    while retry < 3 and not success:
                        command = '%s %s' % (prompt, prompts[prompt])
                        self.child.sendline(command)
                        (success, response) = self._check_expect_response(
                                command, self.oper_prompt, timeout=5, close_child=False)
                        if not success:
                            retry += 1

                    if not success:
                        return response
                    response = self._validate_buffer(
                            command, self.child.before)
                    if response.error is not None:
                        return response

                command = 'paginate false'
                self.child.sendline(command)
                (success, response) = self._check_expect_response(
                        command, self.oper_prompt)
                if not success:
                    return response
                response = self._validate_buffer(
                        command, self.child.before)
                if response.error is not None:
                    return response
            else:
                for prompt in prompts:
                    command = '%s %s' % (prompt, prompts[prompt])
                    self._send_command(command)
                    buf = self._wait(self.oper_prompt)
                    if isinstance(buf, Reply):
                        response = buf
                    else:
                        response = self._validate_buffer(command, buf)
                    if response.error is not None:
                        return response

                command = 'paginate false'
                self._send_command(command)
                buf = self._wait(self.oper_prompt)
                if isinstance(buf, Reply):
                    response = buf
                else:
                    response = self._validate_buffer(command, buf)
                if response.error is not None:
                    return response

        commit = False
        commit_response = None
        exit_commands = ['commit', 'show configuration diff', 'validate']

        if any(x in commands for x in exit_commands):
            commit_response = self._commit_handler(commands)
            commit = True

        if commit is False:
            for command in commands:
                if 'encoding' in kwargs:
                    encoding = kwargs['encoding']
                    if encoding is not None:
                        command = command + ' | display %s' % (encoding)

                if self.arcos_shell:
                    if self.session.local is True:
                        try:
                            self.child.sendline(command)
                            self.child.expect(self.oper_prompt,
                                    timeout=self.timeout)
                            response = self._validate_buffer(command,
                                    self.child.before)
                            if response.error is not None:
                                return response
                            buf = response.message
                        except pexpect.TIMEOUT:
                            return Reply(Error.PROCESS_TIMEOUT,
                                'Command [{}] timed out'.format(
                                    command))
                    else:
                        self._send_command(command)
                        buf = self._wait(self.oper_prompt)
                else:
                    return self._shell_command(command)

        ## For now, each call to _interactive_command() spawns a
        ## new shell.  When this is the case, ensure there is some
        ## cleanup to ensure that locks are not being held for
        ## future callers
        ##
        ## TODO: Move session closure for handling at the manager
        ## (session) level
        if self.arcos_shell:
            if self.session.local is True:
                self.child.close()

        if commit:
            response.error = commit_response.error
            response.message = commit_response.message
        else:
            response.error = None
            response.message = self._cleanse_buffer(buf)
        return response

    def _shell_command(self, command):
        """Execute an underlying shell command

        The _shell_command() is an internal API that is invoked as
        part of the public command() API should the user context
        be that of an underlying shell (e.g. non-ArcOS CLI).

        Args:
            command: A string value representing a single shell
                command.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        if self.session.local is False:
            stdin, stdout, stderr = self.session.exec_command(command)
            response = Reply()
            if stdout.channel.recv_exit_status() != 0:
                response.error = Error.SHELL_ERROR
                response.message = stderr.read().rstrip()
            else:
                response.error = None
                response.message = stdout.read()
            return response
        else:
            self.child = pexpect.spawn(command, encoding='UTF-8')
            self.child.expect(pexpect.EOF, timeout=self.timeout)
            result = self.child.before
            response = Reply()
            response.error = None
            response.message = result
            return response

    def close_session(self):
        """Close a local/remote transport session

        When this function is invoked, close the transport
        session.  Note that this function is currently only
        implemented for remote sessions (e.g. SSH)
        """
        if self.session.local is False:
            self.session.close()

    def command(self, command, **kwargs):
        """Execute a single operational command

        Execute a single operational command and return the result
        in the encoding requested by the client by way of the kwarg
        key 'encoding'.

        Args:
            command: A string value representing a single operational
                command.
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        if self.session.local is False:
            if self.arcos_shell:
                 output = self._interactive_command([command], **kwargs)
                 return output
            else:
                if 'cli' in kwargs:
                    if kwargs['cli'] is not None:
                        return self._interactive_command([command], **kwargs)
                    else:
                        return self._shell_command(command)
                else:
                    return self._shell_command(command)
        else:
            if 'cli' in kwargs:
                if kwargs['cli'] is not None:
                    return self._interactive_command([command], **kwargs)
                else:
                    return self._shell_command(command)
            else:
                return self._shell_command(command)

    def execute(self, commands, **kwargs):
        """Execute a list of configuration commands

        Execute a sequential list of commands.  This API is intended
        to be used mainly for a sequence of configuration commands
        that return a single data payload (e.g. transaction
        confirmation).  The list must contain all qualified commands
        to be executed in order.

        e.g.
            commands = [
                'config',
                'interface swp1 enabled false',
                'commit',
                'end'
            ]

        Args:
            commands: A list of sequential commands to invoke
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        if self.session.local:
            if self.arcos_shell:
                return self._interactive_command(commands, **kwargs)
            else:
                if 'cli' in kwargs:
                    if kwargs['cli'] is not None:
                        return self._interactive_command(commands, **kwargs)
                    else:
                        return self._noninteractive_command(commands, **kwargs)
                else:
                    return self._noninteractive_command(commands, **kwargs)
        else:
            if self.arcos_shell:
                return self._interactive_command(commands, **kwargs)
            else:
                if 'cli' in kwargs:
                    if kwargs['cli'] is not None:
                        return self._interactive_command(commands,
                                **kwargs)
                    else:
                        return Reply(error=Error.OPERATION_ERROR,
                                message='This operation is not permitted '
                                'from the users shell context')
                else:
                    return Reply(error=Error.OPERATION_ERROR,
                            message='This operation is not permitted '
                            'from the users shell context')

    def get_config(self, **kwargs):
        """Retrieve the configuration from the running datastore

        Retrieve the full configuration from the running datastore.
        If the user's shell context is a standard shell (e.g. bash)
        and the caller is remote, then the cli=True argument must be
        passed.  If the caller is local and cli=False, then the
        non-interactive code path is taken automatically to pipe in
        commands to confd_cli.

        The 'encoding' argument if passed in will return data in the
        appropriate format (e.g. xml, json, text)

        Args:
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, the appropriate
            data payload is returned in the message field.  If the
            reply is a failure, an appropriate error code is set
            along with a message description indicating the failure.
        """
        commands = ['show running-config']

        if self.session.local:
            if self.arcos_shell:
                return self._interactive_command(commands, **kwargs)
            else:
                if 'cli' in kwargs:
                    if kwargs['cli'] is not None:
                        return self._interactive_command(commands,
                                **kwargs)
                    else:
                        return self._noninteractive_command(commands,
                                **kwargs)
                else:
                    return self._noninteractive_command(commands,
                            **kwargs)
        else:
            if self.arcos_shell:
                return self._interactive_command(commands, **kwargs)
            else:
                if 'cli' in kwargs:
                    if kwargs['cli'] is not None:
                        return self._interactive_command(commands,
                                **kwargs)
                    else:
                        return Reply(error=Error.OPERATION_ERROR,
                                message='This operation is not permitted '
                                'from the users shell context')
                else:
                    return Reply(error=Error.OPERATION_ERROR,
                            message='This operation is not permitted '
                            'from the users shell context')

    def load_config(self, filename, **kwargs):
        """Load a configuration from file contents

        Load a configuration from a file.  If the caller is remote
        then the 'FEED' load operation is performed by executing
        each command over the remote channel.  For this operation,
        only CLI syntax is supported within the configuration file.
        If the caller is remote then 'MERGE', 'OVERRIDE', and 'REPLACE'
        operations are supported and the file contents can be encoded
        as XML or CLI plain text.

        Datastore locks are achieved by passing in a mode.  Either
        'terminal' (private), 'shared' or 'exclusive' are supported.

        This API handles the abstraction of locks, loading and the
        subsequent commit of the transaction.  Validation and commit
        comments are also supported by way of passing in 'comment',
        'check', or 'validate' arguments.

        For large configurations, it is possible that the default
        timeout for this API does not suffice.  If this is the case
        the caller can pass in a custom 'timeout' argument.

        Args:
            filename: A string representing a local filename
            kwargs: A dict of keyword arguments passed to respective
                functions.
        Returns:
            A Reply() object indicating success/failure along with a
            message.  If the reply is successful, a 'Commit Successful'
            message is returned.  If the reply is a failure, an
            appropriate error code is set along with a message
            description indicating the failure.
        """
        ## While all encodings are a common class object, current
        ## load operations do not support the loading of JSON encoded
        ## data so return to the caller immediately
        if 'encoding' in kwargs:
            if kwargs['encoding'] is Encoding.JSON:
                return Reply(error=Error.UNSUPPORTED_ENCODING,
                        message='JSON encoding is not supported for load '
                        'operations')

        if 'timeout' in kwargs:
            self.timeout = kwargs['timeout']

        if 'mode' in kwargs:
            self.mode = kwargs['mode']
        else:
            self.mode = 'terminal'

        commit_comment = kwargs.get('comment', None)
        check = kwargs.get('check', False)
        validate = kwargs.get('validate', False)

        commands = ['config {}'.format(self.mode)]

        if self.session.local:
            if 'load_operation' in kwargs:
                if kwargs['load_operation'] is not None:
                    commands += ['load {} {}'.format(
                        kwargs['load_operation'], filename)]
                else:
                    fh = open(filename, 'r')
                    commands += fh.readlines()
                    fh.close()
        else:
            if 'load_operation' in kwargs:
                ## Only the FEED operation is supported for
                ## remote sessions
                if kwargs['load_operation'] is not None:
                    return Reply(error=Error.OPERATION_ERROR,
                            message='Only the FEED load operation is '
                            'supported for remote connections')

            if 'encoding' in kwargs:
                ## Only TEXT encoding is supported for remote load
                ## FEED operations
                if kwargs['encoding'] is not None:
                    return Reply(error=Error.UNSUPPORTED_ENCODING,
                            message='Only TEXT (CLI) encoding is '
                            'supported for remote load operations')

            if 'cli' in kwargs:
                if kwargs['cli'] is None:
                    return Reply(error=Error.OPERATION_ERROR,
                            message='This operation is not permitted '
                            'from the users shell context')
            else:
                return Reply(error=Error.OPERATION_ERROR,
                        message='This operation is not permitted '
                        'from the users shell context')

            fh = open(filename, 'r')
            commands += fh.readlines()
            fh.close()

        if not check and not validate:
            if commit_comment is None:
                commands += ['commit', 'end']

            else:
                commands += ['commit comment "{}"'.format(commit_comment), 'end']

        elif check:
            commands += ['show configuration diff', 'end no-confirm']
        elif validate:
            commands += ['validate', 'end no-confirm']

        if self.arcos_shell:
            return self._interactive_command(commands, **kwargs)

        else:
            if 'cli' in kwargs:
                if not kwargs['cli'] :
                    return self._noninteractive_command(commands, **kwargs)
                elif kwargs['cli'] is not None:
                    return self._interactive_command(commands, **kwargs)
            else:
                return self._noninteractive_command(commands, **kwargs)

