#!/usr/bin/env python

from arcapi import errors
from arcapi import manager
from arcapi.types import Handler

def main():
    m = manager.connect(handler=Handler.CLI)

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
