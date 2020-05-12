import json
import logging
import time
from arcapi import errors
from arcapi import manager
from arcapi.types import Encoding
from arcapi.types import Handler

logger = logging.getLogger('arcapi_collector')

class ArcosCollector(object):
    def __init__(self, host=None, address=None, credential={}, port=22, timeout=15, retry=3, parsers=None,
                 context=None, use_hostname=False, collect_facts=True):
        self.hostname = host
        self.host = address
        self.__credential = credential
        self.__port = port
        self.__timeout = timeout
        self.__retry = retry
        self.__is_connected = False
        self.parsers = parsers
        if context:
            self.context = {k: v for i in context for k, v in i.items()}
        else:
            self.context = None
        self.facts = {}
        self.__collect_facts = collect_facts
        self.manager = None
        self.__use_arcos_cli = True if self.__credential['username'] == 'root' else False

    def connect(self):
        logger.info('Connecting to host %s', self.hostname)

        if self.__is_connected:
            return self.__is_connected

        self.manager = manager.connect(
                host=self.host,
                handler=Handler.CLI,
                port=self.__port,
                username=self.__credential['username'],
                password=self.__credential['password'],
                hostkey_add=True)

        self.__is_connected = True

    def collect(self, command):
        # find the command to execute from the parser directly
        parser = self.parsers.get_parser_for(command)
        data = self.send_command(parser['data']['parser']['command'])
        if data is None:
            return None

        if parser['data']['parser']['type'] == 'textfsm':
            data = etree.tostring(data)

        datapoints = self.parsers.parse(input=command, data=data)
        if datapoints is not None:
            measurement = self.parsers.get_measurement_name(input=command)
            timestamp = time.time_ns()
            for datapoint in datapoints:
                if not datapoint['fields']:
                    continue
                if datapoint['measurement'] == None:
                    datapoint['measurement'] = measurement
                datapoint['tags'].update(self.facts)
                if self.context:
                    datapoint['tags'].update(self.context)
                datapoint['timestamp'] = timestamp
                yield datapoint
        else:
            logger.warn('No parser found for command > %s',command)
            return None
        
        #use arcapi to run command
        #data = self.send_command(command=command,encoding=Encoding.JSON, cli=True)
        #print(data)

    def collect_facts(self):
        if not self.__is_connected:
            return

        self.facts['device'] = self.hostname
        if self.__collect_facts:

            logger.info('[%s]: Collection Facts on device', self.hostname)
            
            fact_data = self.send_command(command='show version',encoding=Encoding.JSON)
            if fact_data:
                base_data =  fact_data['data']['openconfig-system:system']['arcos-openconfig-system-augments:version']['state']
                self.facts['version'] = base_data['sw-version']
                self.facts['product-model'] = base_data['product-name']
        return True
            
    def send_command(self, command=None, encoding=Encoding.TEXT):

        logger.debug('[%s]: execute : %s', self.hostname, command)
        result = self.manager.command(command=command, encoding=encoding, cli=self.__use_arcos_cli)
        if result.error:
             logger.error("Error found on <%s> executing command: %s, error: %s:", self.hostname, command, result.message)
             return None
        else:
            if encoding == Encoding.TEXT:
                return result.message
            elif encoding == Encoding.JSON:
                return json.loads(result.message)

    def is_connected(self):
        return self.__is_connected

    def close(self):

        if self.__is_connected:
            self.manager.close_session()



