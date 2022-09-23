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


import importlib
import logging
from multiprocessing import Process, Pipe


class out_of_process_proxy():

    # NOTE: oop_loader code runs in a separate process
    def oop_loader(self, oop_target, input_ports, output_ports, input_pdu_pipe, output_pdu_pipe, params):
        # Load the target OOP module and class; if successful, invoke its
        # main loop function
        try:
            oop_target_module_name = '.'.join(oop_target[0:-1])
            oop_target_module = importlib.import_module(oop_target_module_name)
            oop_target_class = oop_target[-1]
            if hasattr(oop_target_module, oop_target_class):
                try:
                    self.oop_class = getattr(oop_target_module, oop_target_class)(
                        input_ports=input_ports,
                        output_ports=output_ports,
                        input_pdu_pipe=input_pdu_pipe,
                        output_pdu_pipe=output_pdu_pipe,
                        params=params)
                    self.oop_class.main_loop()
                except:
                    logging.warning(f'Could not instantiate target class {oop_target_class} - incoming PDUs will be dropped')
            else:
                logging.warning(f'No class {oop_target_class} in {oop_target_module_name} - incoming PDUs will be dropped')
        except:
            logging.warning(f'Could not import {oop_target_module_name} - incoming PDUs will be dropped')

    def __init__(self, input_ports, output_ports, send_pdu_fn, params):
        logging.info('out_of_process_proxy: instantiating')

        # Validate parameters
        for required_param in ['oop_target']:
            if required_param not in params:
                raise KeyError(f'out_of_process_proxy: Required parameter \'{required_param}\' not specified')
        oop_target = params['oop_target'].split('.')
        if len(oop_target) < 2:
            raise ValueError(f'out_of_process_proxy: oop_target must be in module.class format')

        self.child_process = None

        # Create pipes 
        self.send_pdu_fn = send_pdu_fn
        self.proxy_input_pdu_pipe_end, self.oop_input_pdu_pipe_end = Pipe()
        self.proxy_output_pdu_pipe_end, self.oop_output_pdu_pipe_end = Pipe()

        # Create loader process and send it on its way
        self.child_process = Process(target=self.oop_loader,
            args=(oop_target, input_ports, output_ports, 
                self.oop_input_pdu_pipe_end, self.oop_output_pdu_pipe_end,
                params))
        self.child_process.start()

    def __del__(self):
        if self.child_process:
            self.child_process.join()

    def receive_pdu(self, port_name, data):
        # Send the PDU to the target via the pipe
        self.proxy_input_pdu_pipe_end.send((port_name, data))
        # See if there are any PDUs from the target end we need to issue
        if self.proxy_output_pdu_pipe_end.poll():
            # TODO: this'll need some exception handling
            (send_port_name, send_pdu) = self.proxy_output_pdu_pipe_end.recv()
            self.send_pdu_fn(send_port_name, send_pdu)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    INPUT_PORTS = ['tc_pdus', 'cc_pdus']
    OUTPUT_PORTS = ['radio_freq', 'radio_gain', 'cc_offset', 'tc_offset']
    tui = out_of_process_proxy(INPUT_PORTS, OUTPUT_PORTS, None,
        {'site_file': '/tmp/trs_site_2_2022.csv',
         'tg_file': '/tmp/trs_tg_2_enhanced_2022.csv',
         'site_id': '1.7',
         'oop_target': 'scanner.p25_scanner.ccmon_oop_ws.ccmon_oop_ws'})