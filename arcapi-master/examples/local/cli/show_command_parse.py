#!/usr/bin/env python

import json
import string

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
    interfaces = message['data']['openconfig-interfaces:interfaces']['interface']
    result = {}
    for interface in interfaces:
        name = interface['name']
        try:
            description = interface['state']['description']
        except KeyError:
            description = 'N/A'
        try:
            admin_status = interface['state']['admin-status']
        except KeyError:
            admin_status = 'N/A'
        try:
            oper_status = interface['state']['oper-status']
        except KeyError:
            oper_status = 'N/A'

        result[name] = {}
        result[name]['description'] = description
        result[name]['admin-status'] = admin_status
        result[name]['oper-status'] = oper_status
    return result


def parse_xml(message):
    root = etree.fromstring(message)
    ns = {
            'tailf': 'http://tail-f.com/ns/config/1.0',
            'oc-if': 'http://openconfig.net/yang/interfaces'
    }
    interfaces = root.xpath('/tailf:config/oc-if:interfaces/oc-if:interface', namespaces=ns)
    result = {}
    for interface in interfaces:
        name = interface.xpath('.//oc-if:name', namespaces=ns)[0].text

        description = 'N/A'
        find_desc = interface.xpath('.//oc-if:state/oc-if:description', namespaces=ns)
        if find_desc:
            description = find_desc[0].text
            if description is None:
                description = ''

        admin_status = 'N/A'
        find_admin_status = interface.xpath('.//oc-if:state/oc-if:admin-status', namespaces=ns)
        if find_admin_status:
            admin_status = find_admin_status[0].text

        oper_status = 'N/A'
        find_oper_status = interface.xpath('.//oc-if:state/oc-if:oper-status', namespaces=ns)
        if find_oper_status:
            oper_status = find_oper_status[0].text

        result[name] = {}
        result[name]['description'] = description
        result[name]['admin-status'] = admin_status
        result[name]['oper-status'] = oper_status
    return result


def parse(message, encoding):
    if encoding == Encoding.XML:
        return parse_xml(message)
    if encoding == Encoding.JSON:
        return parse_json(message)
    else:
        raise NotImplementedError

def main():
    m = manager.connect(handler=Handler.CLI)

    encoding = Encoding.TEXT
    if options.xml:
        encoding = Encoding.XML
    if options.json:
        encoding = Encoding.JSON

    result = m.command(command='show interface', encoding=encoding, cli=True)
    if result.error == None:
        try:
            result = parse(result.message, encoding)
            print('%-15s %-35s %-15s %-15s' % ('Interface', 'Description', 'Admin Status', 'Oper Status'))
            print('-' * 85)
            sorted_result = sorted(result, key=lambda x: int(x.lower().lstrip(string.ascii_lowercase)))
            for interface in sorted_result:
                print('%-15s %-35s %-15s %-15s' % (
                    interface, result[interface]['description'], result[interface]['admin-status'],
                    result[interface]['oper-status']))
        except NotImplementedError:
            print('Error: Parsing support not available for cli output')

    else:
        print('Error: {}'.format(errors.name(result.error)))
        print('Message: {}'.format(result.message))

if __name__ == '__main__':
    main()
