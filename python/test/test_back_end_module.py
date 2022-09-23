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

import logging
from multiprocessing import Process, Pipe

class test_back_end():
    def __init__(self, input_ports, output_ports, send_pdu_fn, params):
        logging.info('test_back_end class instantiating')
        logging.info(f'  input_ports={input_ports}')
        logging.info(f'  output_ports={output_ports}')
        logging.info(f'  params={params}')
        self.send_pdu = send_pdu_fn
        self.input_pdu_count = dict([(input_port, 0) for input_port in input_ports])
        if 'cc_offset' in params:
            self.cc_offset = float(params['cc_offset'])
            self.do_tune_cc = True

    def receive_pdu(self, port, data):
        assert port in self.input_pdu_count
        self.input_pdu_count[port] = self.input_pdu_count[port] + 1
        logging.info(f'test_back_end: PDU on port {port} received (#{self.input_pdu_count[port]}): {data}')
        if self.do_tune_cc and port == 'cc_pdus':
            logging.info('test_back_end: sending PDU to tune control channel')
            self.send_pdu('cc_offset', {'type': 'float', 'value': self.cc_offset})
            self.do_tune_cc = False


class test_back_end_out_of_process(test_back_end):
    def oop_receive_pdu(self):
        logging.info(f'test_back_end_oop: oop_receive_pdu started')
        while True:
            try:
                (port, data) = self.oop_input_pdu_pipe_end.recv()
                test_back_end.receive_pdu(self, port, data)
            except BaseException as e:
                logging.info(f'test_back_end_oop: oop_receive_pdu caught exception {type(e)}')
                break
        logging.info(f'test_back_end_oop: oop_receive_pdu ending')

    def oop_send_pdu(self, port_name, pdu):
        logging.info(f'test_back_end_oop: oop_send_pdu called')
        try:
            self.oop_output_pdu_pipe_end.send((port_name, pdu))
        except BaseException as e:
            logging.info(f'test_back_end_oop: oop_send_pdu caught exception {type(e)}')

    def __init__(self, input_ports, output_ports, send_pdu_fn, params):
        logging.info('test_back_end_out_of_process instantiating')
        # Tell the back end to use our special OOP send_pdu function (which
        # will forward to the real one passed by the front end interface)
        test_back_end.__init__(self, input_ports, output_ports, self.oop_send_pdu, params)
        self.real_send_pdu = send_pdu_fn
        self.inproc_input_pdu_pipe_end, self.oop_input_pdu_pipe_end = Pipe()
        self.inproc_output_pdu_pipe_end, self.oop_output_pdu_pipe_end = Pipe()
        self.log_process = Process(target=self.oop_receive_pdu)
        self.log_process.start()

    def __del__(self):
        self.log_process.join()

    def receive_pdu(self, port_name, data):
        self.inproc_input_pdu_pipe_end.send((port_name, data))
        # See if there are any PDUs from the OOP end we need to issue
        if self.inproc_output_pdu_pipe_end.poll():
            # TODO: this'll need some exception handling
            (send_port_name, send_pdu) = self.inproc_output_pdu_pipe_end.recv()
            self.real_send_pdu(send_port_name, send_pdu)
