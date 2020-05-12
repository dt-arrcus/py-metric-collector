#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Encoding
from arcapi.types import Handler

from optparse import OptionParser

parser = OptionParser()
parser.add_option('--json', dest='json', action='store_true',
        help='Output JSON encoding')
parser.add_option('--xml', dest='xml', action='store_true',
        help='Output XML encoding')
(options, args) = parser.parse_args()

def main():
    m = manager.connect()

    encoding = Encoding.TEXT
    if options.xml:
        encoding = Encoding.XML
    if options.json:
        encoding = Encoding.JSON

    result = m.get_config(encoding=encoding, cli=True)
    if result.error == None:
        print(result.message)
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
