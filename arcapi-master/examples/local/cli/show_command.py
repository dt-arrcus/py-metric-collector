#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Encoding
from arcapi.types import Handler

from getpass import getpass
from optparse import OptionParser

import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')

parser = OptionParser()
parser.add_option('--json', dest='json', action='store_true',
        help='Output JSON encoding')
parser.add_option('--xml', dest='xml', action='store_true',
        help='Output XML encoding')
(options, args) = parser.parse_args()

def main():
    m = manager.connect(
            host='localhost',
            handler=Handler.CLI)

    encoding = Encoding.TEXT
    if options.xml:
        encoding = Encoding.XML
    if options.json:
        encoding = Encoding.JSON

    result = m.command(command='show version', encoding=encoding, cli=True,
            timeout=120)
    if result.error == None:
        if result.message == '':
            print('No output returned')
        else:
            print(result.message)
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
