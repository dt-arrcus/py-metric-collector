#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Handler
from arcapi.types import LoadOperation

from optparse import OptionParser

parser = OptionParser()
parser.add_option('--filename', dest='filename', type='str',
        help='Configuration filename (Absolute Path)')
parser.add_option('--merge', dest='merge', action='store_true',
        help='Merge with existing configuration (XML|CLI)')
parser.add_option('--override', dest='override', action='store_true',
        help='Overwrite existing configuration (XML|CLI)')
parser.add_option('--replace', dest='replace', action='store_true',
        help='Replace existing configuration (XML|CLI)')
(options, args) = parser.parse_args()

def main():
    if not options.filename:
        options.filename = raw_input('Enter the configuration absolute path: ')

    m = manager.connect()

    # Default 'FEED' operation only takes CLI syntax file
    operation = LoadOperation.FEED

    if options.merge:
        operation = LoadOperation.MERGE
    if options.override:
        operation = LoadOperation.OVERRIDE
    if options.replace:
        operation = LoadOperation.REPLACE

    result = m.load_config(filename=options.filename, load_operation=operation, cli=True)
    if result.error == None:
        print('Message: {}'.format(result.message))
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
