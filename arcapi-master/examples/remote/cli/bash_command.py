#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Handler

from getpass import getpass
from optparse import OptionParser

import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')

parser = OptionParser()
parser.add_option('--host', dest='host', type='str',
        help='Hostname')
parser.add_option('--port', dest='port', type='int',
        default=22, help='TCP Port (SSH)')
parser.add_option('--username', dest='username', type='str',
        help='Username')
(options, args) = parser.parse_args()

def main():
    if not options.host:
        options.host = raw_input('Enter a hostname: ')

    if not options.username:
        options.username = raw_input('Enter a valid username: ')

    password = getpass('Enter Password: ')

    m = manager.connect(
            host=options.host,
            handler=Handler.CLI,
            port=options.port,
            username=options.username,
            password=password,
            hostkey_add=True)

    result = m.command(command='ls -la', shell=True)
    if result.error == None:
        print(result.message)
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

    print('-' * 80)

    result = m.command(command='uname -a', shell=True)
    if result.error == None:
        print(result.message)
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
