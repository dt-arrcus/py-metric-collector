#!/usr/bin/env python

import json

from arcapi import errors
from arcapi import manager
from arcapi.types import Encoding
from arcapi.types import Handler

from lxml import etree
from optparse import OptionParser

parser = OptionParser()
parser.add_option('--json', dest='json', action='store_true',
        help='Output JSON encoding')
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
    m = manager.connect()

    encoding = Encoding.TEXT
    if options.xml:
        encoding = Encoding.XML
    if options.json:
        encoding = Encoding.JSON

    result = m.get_config(encoding=encoding, cli=True)
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
