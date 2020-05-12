#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Handler

def main():
    m = manager.connect()

    config_list = [
            'config',
            'no int swp10',
            'no int swp11',
            'no int swp12',
            'no int swp13',
            'commit',
            'end']

    result = m.execute(config_list, cli=True)
    if result.error == None:
        print('Message: {}'.format(result.message))
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
