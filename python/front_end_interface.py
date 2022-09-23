#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2022 Aaron Rossetto <aaron.rossetto@gmail.com>.
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#


import numpy
from gnuradio import gr
import importlib
import json
import logging
import pmt
import time



class front_end_interface(gr.basic_block):
    @staticmethod
    def _shorten_json(input_string, length=30):
        s = input_string.strip()
        if len(s) <= length:
            return s
        start_len = (length - 5) // 2;
        end_len = (length - 5) - start_len;
        return s[:start_len] + ' ... ' + s[-end_len:]


    """
    docstring for block front_end_interface
    """
    def __init__(self, input_port_list=[], output_port_list=[],
        back_end_module_class_name='',
        back_end_module_parameters=''):
        gr.basic_block.__init__(self,
            name='front_end_interface',
            in_sig=None,
            out_sig=None)

        # Parase parameters into a dictionary
        param_dict = {}
        for param in back_end_module_parameters.split(','):
            param = param.strip()
            (key, *value) = param.split('=')
            if len(value) > 0:
                param_dict[key.strip()] = value[0].strip()
            else:
                param_dict[key.strip()] = ''

        numeric_level = logging.WARNING
        log_format_string = '[gr-scanner %(levelname)s] %(message)s'
        if 'loglevel' in param_dict:
            loglevel = param_dict['loglevel'].upper()
            numeric_level = getattr(logging, loglevel, None)
            if not isinstance(numeric_level, int):
                raise ValueError(f'Invalid log level {loglevel}')
        logging.basicConfig(level=numeric_level, format=log_format_string)

        # Load the back end module and instantiate the class (if possible)
        self.back_end_module = None
        self.back_end_class = None
        if back_end_module_class_name != '':
            back_end_name_elements = back_end_module_class_name.split('.')
            if len(back_end_name_elements) >= 2:
                back_end_module_name = '.'.join(back_end_name_elements[0:-1])
                back_end_class_name = back_end_name_elements[-1]
                try:
                    back_end_module = importlib.import_module(back_end_module_name)
                    if hasattr(back_end_module, back_end_class_name):
                        try:
                            self.back_end_class = getattr(back_end_module, back_end_class_name)(
                                input_ports=input_port_list,
                                output_ports=output_port_list,
                                send_pdu_fn=self.send_pdu,
                                params=param_dict)
                        except:
                            logging.warning(f'Could not instantiate back end class {back_end_class_name} - incoming PDUs will be dropped')
                    else:
                        logging.warning(f'No class {back_end_class_name} in {back_end_module_name} - incoming PDUs will be dropped')
                except:
                    logging.warning(f'Could not import {back_end_module_name} - incoming PDUs will be dropped')
            else:
                logging.warning(f'Invalid format for module and class name - incoming PDUs will be dropped')
        else:
            logging.warning(f'No back end module specified - incoming PDUs will be dropped')

        # Create the input and output port name maps
        #   Maps user's chosen port name to the actual numbered GR port name
        #   'inx'/'outx'
        self.input_port_name_map = dict(
            [(chan[1], 'in{}'.format(chan[0])) for chan in enumerate(input_port_list)])

        self.output_port_name_map = dict(
            [(chan[1], 'out{}'.format(chan[0])) for chan in enumerate(output_port_list)])

        for (user_name, gr_port_name) in self.input_port_name_map.items():
            self.message_port_register_in(pmt.intern(gr_port_name))
            self.set_msg_handler(pmt.intern(gr_port_name),
                lambda pdu, port_name=user_name:
                    self.receive_pdu(port_name, pdu))

        for (_, gr_port_name) in self.output_port_name_map.items():
            self.message_port_register_out(pmt.intern(gr_port_name))

    def receive_pdu(self, port_name, pdu_data):
        if not pmt.is_u8vector(pdu_data):
            return

        pdu_str = ''.join([chr(x) for x in pmt.u8vector_elements(pdu_data)])
        pdu_json = json.loads(pdu_str)

        if self.back_end_class:
            logging.debug(f'receive_pdu: {front_end_interface._shorten_json(pdu_str)} on port {port_name}')
            self.back_end_class.receive_pdu(port_name, pdu_json)
        else:
            logging.warning(f'receive_pdu: dropping {front_end_interface._shorten_json(pdu_str)} on port {port_name} (no handler)')

    def send_pdu(self, port_name, json_data):
        # example: port_name = 'radio_freq', json_data = {'type': 'float', 'value': '850000000'}
        # Note that port_name is the user's port_name name, not the GR port_name name
        if not all(key in json_data for key in ['type', 'value']):
            return

        if self.output_port_name_map.get(port_name, None):
            data_type = json_data['type']
            if data_type == 'float':
                data_as_pmt = pmt.from_double(float(json_data['value']))
                self.message_port_pub(pmt.intern(self.get_gr_port_name(port_name)), data_as_pmt)
            else:
                logging.warning(f'send_pdu: dropping {front_end_interface._shorten_json(str(json_data))} on port {port_name} (bad type)')    
        else:
            logging.warning(f'send_pdu: dropping {front_end_interface._shorten_json(str(json_data))} on port {port_name} (no mapping)')

    def get_gr_port_name(self, user_name):
        if user_name in self.input_port_name_map:
            return self.input_port_name_map[user_name]

        if user_name in self.output_port_name_map:
            return self.output_port_name_map[user_name]

        return None


if __name__ == "__main__":

    class test_json_pdu_sender(gr.basic_block):
        def __init__(self):
            gr.basic_block.__init__(self,
                name='test_pdu_sender',
                in_sig=None,
                out_sig=None)

            self.message_port_register_out(pmt.intern('pdu_out'))

        def send_json_pdu(self, json_data):
            json_as_string = json.dumps(json_data)
            pdu_data = pmt.make_u8vector(len(json_as_string), ord(' '))
            for i in range(len(json_as_string)):
                pmt.u8vector_set(pdu_data, i, ord(json_as_string[i]))

            self.message_port_pub(pmt.intern('pdu_out'), pdu_data)


    class test_typed_pdu_receiver(gr.basic_block):
        def __init__(self):
            gr.basic_block.__init__(self,
                name='test_pdu_receiver',
                in_sig=None,
                out_sig=None)

            self.message_port_register_in(pmt.intern('pdu_in'))
            self.set_msg_handler(pmt.intern('pdu_in'), self.receive_pdu)

        def receive_pdu(self, pdu):
            value = pmt.to_double(pdu)
            logging.debug(f'test_typed_pdu_receiver received {value}')

    tb = gr.top_block()
    fei_receiver = front_end_interface(['receiver_0', 'receiver_1'], [], '')
    fei_sender = front_end_interface([], ['sender_0', 'sender_1'], '')
    tjps0 = test_json_pdu_sender()
    tjps1 = test_json_pdu_sender()
    ttpr0 = test_typed_pdu_receiver()
    ttpr1 = test_typed_pdu_receiver()

    tb.msg_connect(tjps0, 'pdu_out', fei_receiver, fei_receiver.get_gr_port_name('receiver_0'))
    tb.msg_connect(tjps1, 'pdu_out', fei_receiver, fei_receiver.get_gr_port_name('receiver_1'))
    tb.msg_connect(fei_sender, fei_sender.get_gr_port_name('sender_0'), ttpr0, 'pdu_in')
    tb.msg_connect(fei_sender, fei_sender.get_gr_port_name('sender_1'), ttpr1, 'pdu_in')

    tb.start()

    tjps0.send_json_pdu({'key': 'value', 'key2': [0, 1, 2], 'should_go_to': 'receiver_0'})
    tjps1.send_json_pdu({'key': 'eulav', 'key3': [-3, -2, 1.5], 'should_go_to': 'receiver_1'})
    fei_sender.send_pdu('sender_0', {'type': 'float', 'value': 3.14})
    fei_sender.send_pdu('sender_1', {'type': 'float', 'value': -2.71828})
    time.sleep(1.5)

    tb.stop()
    tb.wait()
