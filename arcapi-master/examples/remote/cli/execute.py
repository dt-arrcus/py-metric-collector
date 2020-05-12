#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Handler

from getpass import getpass
from optparse import OptionParser

import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')

parser = OptionParser()
parser.add_option('--cli', dest='cli', action='store_true',
        help='Enable ArcOS CLI if not users default shell')
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

    config_list = [
            'config',
            'no int swp10',
            'no int swp11',
            'no int swp12',
            'no int swp13',
            'commit',
            'end']

    result = m.execute(config_list, cli=options.cli)
    if result.error == None:
        print('Message: {}'.format(result.message))
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
