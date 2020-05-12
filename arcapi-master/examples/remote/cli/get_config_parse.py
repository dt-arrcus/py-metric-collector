#!/usr/bin/env python

import json

from arcapi import errors
from arcapi import manager
from arcapi.types import Encoding
from arcapi.types import Handler

from getpass import getpass
from lxml import etree
from optparse import OptionParser

import warnings
warnings.filterwarnings(action='ignore',module='.*paramiko.*')

parser = OptionParser()
parser.add_option('--cli', dest='cli', action='store_true',
        help='Enable ArcOS CLI if not users default shell')
parser.add_option('--host', dest='host', type='str',
        help='Hostname')
parser.add_option('--json', dest='json', action='store_true',
        help='Output JSON encoding')
parser.add_option('--port', dest='port', type='int',
        default=22, help='TCP Port (SSH)')
parser.add_option('--username', dest='username', type='str',
        help='Username')
parser.add_option('--xml', dest='xml', action='store_true',
        help='Output XML encoding')
(options, args) = parser.parse_args()

def parse_json(message):
    message = json.loads(message)
    banner = message['data']['openconfig-system:system']['config']['login-banner']
    return banner

def parse_xml(message):
    root = etree.fromstring(message)
    ns = {
            'tailf': 'http://tail-f.com/ns/config/1.0',
            'oc-sys': 'http://openconfig.net/yang/system'
    }
    banner = root.xpath('/tailf:config/oc-sys:system/oc-sys:config/oc-sys:login-banner', namespaces=ns)[0].text
    return banner

def parse(message, encoding):
    if encoding == Encoding.XML:
        return parse_xml(message)
    if encoding == Encoding.JSON:
        return parse_json(message)
    else:
        raise NotImplementedError

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

    encoding = Encoding.TEXT
    if options.xml:
        encoding = Encoding.XML
    if options.json:
        encoding = Encoding.JSON

    result = m.get_config(encoding=encoding, cli=options.cli)
    if result.error == None:
        try:
            print('Login Banner: {}'.format(parse(result.message, encoding)))
        except NotImplementedError:
            print('Error: Parsing support not available for cli output')
    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
