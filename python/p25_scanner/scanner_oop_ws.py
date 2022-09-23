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

import json
import logging
from multiprocessing import Process, Pipe
from readline import get_completion_type
from scanner.p25_scanner import p25_scanner_back_end
import select
import socket
import time
from wsproto import ConnectionType, WSConnection, ConnectionState
from wsproto.events import (
    AcceptConnection,
    BytesMessage,
    CloseConnection,
    Message,
    Ping,
    Request,
    TextMessage,
)

tag_emoji_map = {
	'Corrections': '⚖️',
	'Data': '🖥️',
	'EMS Dispatch': '🚑',
	'EMS-Tac': '🚑',
	'EMS-Talk': '👨‍⚕️',
	'Fire Dispatch': '🚒',
	'Fire-Tac': '🚒',
	'Fire-Talk': '👨‍🚒',
	'Hospital': '🏥',
	'Interop': '⛓️',
	'Law Dispatch': '🚓',
	'Law Tac': '🚓',
	'Law Talk': '👮',
	'Military': '⚔️',
	'Multi-Dispatch': '🖇️',
	'Multi-Tac': '🖇️',
	'Multi-Talk': '🖇️',
	'Public Works': '🏙️',
	'Schools': '🏫',
	'Security': '🛡️',
	'Transportation': '🚌',
	'Utilities': '🔌'
}

quality_bars = [
    "🔴⚪⚪⚪⚪⚪⚪⚪⚪⚪", # 0-10%
    "🔴🔴⚪⚪⚪⚪⚪⚪⚪⚪", # 10-20%
    "🔴🔴🔴⚪⚪⚪⚪⚪⚪⚪", # 20-30%
    "🔴🔴🔴🔴⚪⚪⚪⚪⚪⚪", # 30-40%
    "🔴🔴🔴🔴🔴⚪⚪⚪⚪⚪", # 40-50%
    "🔴🔴🔴🔴🔴🟡⚪⚪⚪⚪", # 50-60%
    "🔴🔴🔴🔴🔴🟡🟡⚪⚪⚪", # 60-70%
    "🔴🔴🔴🔴🔴🟡🟡🟡⚪⚪", # 70-80%
    "🔴🔴🔴🔴🔴🟡🟡🟡🟢⚪", # 80-90%
    "🔴🔴🔴🔴🔴🟡🟡🟡🟢🟢"  # 90-100%
]

heartbeat_sigils = ["🧡", "❤️"]
priority_sigil = '⭐ '

SCANNER_STATE_SCANNING = 0
SCANNER_PLAYING_AUDIO = 1

class scanner_oop_ws(p25_scanner_back_end.p25_scanner):

    def start_websocket_server(self):
        self.ws_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ws_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ws_server_socket.bind((self.ws_ip, self.ws_port))
        self.ws_server_socket.listen(0)
        logging.info(f'scanner_oop_ws: WS server listening on {self.ws_ip} port {self.ws_port}')

    def handle_websocket_connection(self):
        (client_socket, client_addr) = self.ws_server_socket.accept()
        logging.info(f'scanner_oop_ws: client connected from {client_addr[0]}:{client_addr[1]}')
        # Create a new Websocket server for this client
        ws_server = WSConnection(ConnectionType.SERVER)
        # Add the client's socket and server to the map
        self.ws_clients.update([(client_socket.fileno(), (client_socket, ws_server))])
        self.client_fds.append(client_socket.fileno())

    def handle_websocket_activity(self, client_fd):
        (client_socket, ws_server) = self.ws_clients[client_fd]
        # Read data from client socket and pass into client's Websocket server
        client_data = client_socket.recv(4096)
        ws_server.receive_data(client_data)

        # Get events and handle
        output_data = b''
        for event in ws_server.events():
            if isinstance(event, Request):
                logging.info(f'scanner_oop_ws: accepting Websocket upgrade')
                output_data += ws_server.send(AcceptConnection())
            elif isinstance(event, CloseConnection):
                logging.info(f'scanner_oop_ws: connection closed ({event.code})')
                output_data += ws_server.send(event.response())
                client_socket.send(output_data)
                # Shut down the client
                client_fd = client_socket.fileno()
                client_socket.shutdown(socket.SHUT_WR)
                client_socket.close()
                # Remove it from our tables
                del self.ws_clients[client_fd]
                self.client_fds.remove(client_fd)
                return
            elif isinstance(event, TextMessage):
                request = json.loads(event.data)
                if 'event' in request:
                    event_type = request['event']
                    logging.info(f'scanner_oop_ws: event type \'{event_type}\' received')
                    reply = self.do_handle_websocket_request(request)
                    if reply != None:
                        output_data += ws_server.send(Message(data=json.dumps(reply)))
            elif isinstance(event, Ping):
                logging.info(f'scanner_oop_ws: pong!')
                output_data += ws_server.send(event.response())
        client_socket.send(output_data)

    def broadcast_websocket_message(self, message):
        # Send a message to all Websocket clients
        for client_fd in self.ws_clients:
            (client_socket, ws_server) = self.ws_clients[client_fd]
            if ws_server.state == ConnectionState.OPEN:
                output_data = ws_server.send(Message(data=message))
                client_socket.send(output_data)

    def broadcast_websocket_binary_message(self, bytes_message):
        # Send a message to all Websocket clients
        for client_fd in self.ws_clients:
            (client_socket, ws_server) = self.ws_clients[client_fd]
            if ws_server.state == ConnectionState.OPEN:
                output_data = ws_server.send(BytesMessage(data=bytes_message))
                client_socket.send(output_data)

    def __init__(self, input_ports, output_ports, input_pdu_pipe, output_pdu_pipe, params):
        p25_scanner_back_end.p25_scanner.__init__(self, input_ports, output_ports, self.oop_send_pdu, params)
        logging.info('scanner_oop_ws: instantiating')

        # Map from client's fileno to the client socket and server handling it
        self.ws_clients = dict()
        self.client_fds = []

        # Check parameters
        self.ws_ip = '0.0.0.0'
        self.ws_port = 8001
        if 'ws_ip' in params:
            self.ws_ip = params['ws_ip']
        if 'ws_port' in params:
            self.ws_port = int(params['ws_port'])

        # Save pipes for receiving/sending PDUs from OOP back end
        self.input_pdu_pipe = input_pdu_pipe
        self.output_pdu_pipe = output_pdu_pipe

        # Application-specific data
        self.system_activity = {}
        self.dwell_time = 2000 # milliseconds to 'hold' channel activity
        self.last_cc_stats = {}
        self.last_cc_dus_seen = 0
        self.last_cc_dus_good = 0
        self.next_cc_du_stats_time = 0
        self.last_tc_stats = {}
        self.next_tc_du_stats_time = 0
        self.heartbeat_counter = 0
        self.scan_state = SCANNER_STATE_SCANNING
        self.tc_freq = 0 # current frequency of traffic channel
        self.lo_list = [] # list of locked-out talkgroups
        self.prio_list = [] # list of priority talkgroups

        # Initialize and start the Websocket server
        self.start_websocket_server()
        self.server_fds = [self.input_pdu_pipe.fileno(), self.ws_server_socket.fileno()]

    def __del__(self):
        logging.info('scanner_oop_ws: shutdown')
        self.ws_server_socket.shutdown(socket.SHUT_WR)
        self.ws_server_socket.close()

        # self.http_server_process.join()

    def main_loop(self):
        # Select on PDU reception or Web socket server events
        logging.info('scanner_oop_ws: main loop starting')
        while True:
            try:
                MAIN_LOOP_SELECT_TIMEOUT = 0.1
                rready_fds = self.server_fds + self.client_fds
                (rready_list, wready_list, xready_list) = select.select(
                    rready_fds, [], [], MAIN_LOOP_SELECT_TIMEOUT)
                if self.input_pdu_pipe.fileno() in rready_list:
                    # Data available on input PDU pipe; pass it to p25_scanner
                    # superclass, which will decode it and send it down to us
                    # in some manner
                    (port, data) = self.input_pdu_pipe.recv()
                    self.receive_pdu(port, data)
                if self.ws_server_socket.fileno() in rready_list:
                    # The websocket server socket signals when there's a
                    # client connecting
                    try:
                        self.handle_websocket_connection()
                    except BaseException as e:
                        logging.error(f'scanner_oop_ws: caught exception in handle connection ({type(e)})')
                for client_fd in self.client_fds:
                    # Data is available on a WS client, so handle it
                    if client_fd in rready_list:
                        try:
                            self.handle_websocket_activity(client_fd)
                        except BaseException as e:
                            logging.error(f'scanner_oop_ws: caught exception in client_fd handle ({type(e)})')
                            # Remove defunct client
                            del self.ws_clients[client_fd]
                            self.client_fds.remove(client_fd)
                # Now perform periodic things
                self.do_periodic_work()

            except BaseException as e:
                logging.error(f'scanner_oop_ws: caught exception in main loop ({e})')
                break
        logging.info('scanner_oop_ws: main loop exiting')

    def oop_send_pdu(self, port_name, pdu):
        # If superclass wants to send a PDU, it'll call this function which
        # will send it across the pipe to the back end
        self.output_pdu_pipe.send((port_name, pdu))

    #--------------------------------------------------------------------------
    # Scanner behaviors begin here
    #--------------------------------------------------------------------------
    def expire_frequency(self, freq):
        self.system_activity[freq].update([
            ('tg', ''),
            ('icon', ''),
            ('description', ''),
            ('source', ''),
            ('expiration', 0),
            ('prio', False),
            ('lockout', False),
            ('changed', True)
        ])
        # Was this the traffic channel? If so, time to scan
        if self.scan_state == SCANNER_PLAYING_AUDIO and self.tc_freq == freq:
            # Clear the playing flag['tg']
            self.system_activity[freq].update([
                ('playing', False)
            ])
            # Choose the next audio to play
            self.scan_state = SCANNER_STATE_SCANNING
            self.next_tc_du_stats_time = 0
            self.scan()
        # And finally, update the display
        self.ui_update()

    def do_periodic_work(self):
        # Scan the activity table to see if we need to expire anything
        for freq in self.system_activity:
            expiration = self.system_activity[freq].get('expiration', 0)
            if expiration > 0 and time.monotonic_ns() > expiration:
                self.expire_frequency(freq)

    def do_ui_lo_group(self, freq):
        tg = self.system_activity[freq].get('tg')
        if tg != None:
            if tg in self.lo_list:
                self.lo_list.remove(tg)
                self.system_activity[freq].update([
                    ('lockout', False),
                    ('changed', True)
                ])
            else:
                self.lo_list.append(tg)
                self.system_activity[freq].update([
                    ('lockout', True),
                    ('changed', True)
                ])
                # Was this the traffic channel we just locked out? If so, time to scan
                if self.scan_state == SCANNER_PLAYING_AUDIO and self.tc_freq == freq:
                    # Clear the playing flag['tg']
                    self.system_activity[freq].update([
                        ('playing', False)
                    ])
                    # Choose the next audio to play
                    self.scan_state = SCANNER_STATE_SCANNING
                    self.scan()
        self.do_ui_click_row(freq)

    def do_ui_group_prio(self, freq):
        tg = self.system_activity[freq].get('tg')
        if tg != None:
            if tg in self.prio_list:
                self.prio_list.remove(tg)
                self.system_activity[freq].update([
                    ('prio', False),
                    ('changed', True)
                ])
            else:
                self.prio_list.append(tg)
                self.system_activity[freq].update([
                    ('prio', True),
                    ('changed', True)
                ])
        self.do_ui_click_row(freq)

    def do_handle_websocket_request(self, request):
        logging.info(f'scanner_oop_ws: event {request}')
        event = request.get('event', '')
        if event == 'CLICK_ROW':
            self.do_ui_click_row(request['freq'])
        if event == 'CLICK_BUTTON':
            button = request['button']
            freq = request['freq']
            if button == 'lo_group':
                self.do_ui_lo_group(freq)
            if button == 'group_prio':
                self.do_ui_group_prio(freq)

    def get_icon_for_tg(self, tg):
        # tg 0 == control channel
        if tg == 0:
            return tag_emoji_map['Data']
        tg_info = self.system.tgs.get(tg)
        if tg_info == None:
            return ''
        tag = tg_info['tag']
        return tag_emoji_map.get(tag, '')

    def get_description_for_tg(self, tg):
        # tg 0 == control channel
        if tg == 0:
            return 'Control Channel'
        tg_info = self.system.tgs.get(tg)
        if tg_info == None:
            return f'Unknown talkgroup {tg}'
        return tg_info['description']

    def ui_update(self):
        # Accumulate a list of changed rows
        changed_freqs = [freq for freq in list(self.system_activity) if
            self.system_activity[freq]['changed']]
        # Update those rows
        for freq in changed_freqs:
            self.system_activity[freq]['changed'] = False
            self.broadcast_websocket_message(json.dumps({
                'event': 'UPDATE_ROW',
                'freq': freq,
                'tg': '' if self.system_activity[freq]['control_channel'] else
                    self.system_activity[freq]['tg'],
                'icon': self.system_activity[freq]['icon'],
                'description': (priority_sigil + self.system_activity[freq]['description']) if self.system_activity[freq]['prio'] else
                    self.system_activity[freq]['description'],
                'source': '' if self.system_activity[freq]['control_channel'] else
                    self.system_activity[freq]['source'],
                'lockout': self.system_activity[freq]['lockout'],
                'control': self.system_activity[freq]['control_channel'],
                'active': self.system_activity[freq]['expiration'] > 0,
                'playing': self.system_activity[freq]['playing'],
                'prio': self.system_activity[freq]['prio'],
                'drawer_open': self.system_activity[freq]['drawer_open']
            }))

    def do_ui_click_row(self, freq):
        for known_freq in self.system_activity:
            # The control channel has no button drawer
            if self.system_activity[known_freq]['control_channel']:
                continue

            # If another drawer is open (i.e., not on this frequency), close it
            if freq != known_freq and self.system_activity[known_freq]['drawer_open']:
                self.broadcast_websocket_message(json.dumps({
                    'event': 'HIDE_ROW_BUTTONS',
                    'freq': known_freq
                }))
                self.system_activity[known_freq].update([
                    ('drawer_open', False),
                    ('changed', True)
                ])
            # Toggle this drawer's open/closed status
            if freq == known_freq:
                drawer_open = self.system_activity[freq]['drawer_open']
                self.broadcast_websocket_message(json.dumps({
                    'event': 'HIDE_ROW_BUTTONS' if drawer_open else 'SHOW_ROW_BUTTONS',
                    'freq': freq
                }))
                self.system_activity[freq].update([
                    ('drawer_open', not drawer_open),
                    ('changed', True)
                ])
            self.ui_update()

    def scan(self):
        if self.scan_state == SCANNER_PLAYING_AUDIO:
            # We're already playing audio. We only want to change channels
            # if we're not currently listening to a priority channel and there's
            # a priority channel available to listen to.
            if self.system_activity[self.tc_freq]['tg'] in self.prio_list:
                # The talkgroup on the traffic channel is already a priority
                # channel. Let it play until completion.
                return
            freqs = sorted(list(self.system_activity))
            # Find the next eligible frequency to listen to
            index = freqs.index(self.tc_freq)
            for i in range(1, len(freqs)):
                next_tc_freq = freqs[(index + i) % len(freqs)]
                # Eligible frequency is not control channel, expiration > 0
                # (i.e. active), and talkgroup is in the priority list
                if not self.system_activity[next_tc_freq]['control_channel'] and \
                    self.system_activity[next_tc_freq]['expiration'] > 0 and \
                    self.system_activity[next_tc_freq]['tg'] in self.prio_list:
                        # Mark old channel as not playing
                        self.system_activity[self.tc_freq].update([
                            ('playing', False),
                            ('changed', True)
                        ])
                        # Make this the traffic channel
                        self.tc_freq = next_tc_freq
                        # Mark it as playing
                        self.system_activity[next_tc_freq].update([
                            ('playing', True),
                            ('changed', True)
                        ])
                        # Tune it
                        self.tune_traffic_channel(self.tc_freq)
                        self.next_tc_du_stats_time = time.monotonic_ns() + 500000000
                        self.last_tc_stats = {}
                        self.scan_state = SCANNER_PLAYING_AUDIO
                        # Update the UI
                        self.ui_update()
                        # And we're done
                        return
            # No eligible priority channels found; keep playing whatever is
            # already playing.
            return

        # No audio is currently playing, so scan for the next frequency to play
        index = 0
        # Get a list of all frequencies we know about (sorted)
        freqs = sorted(list(self.system_activity))
        if self.tc_freq in freqs:
            # Find the next eligible frequency to listen to
            index = freqs.index(self.tc_freq)
        elif self.tc_freq == 0:
            # Search the entire list for something to listen to
            index = -1
        for i in range(1, len(freqs)):
            next_tc_freq = freqs[(index + i) % len(freqs)]
            # Eligible frequency is tg != 0 (i.e., not the control channel),
            # and expiration > 0 (i.e., there's been recent activity)
            # and channel is not locked out
            if not self.system_activity[next_tc_freq]['control_channel'] and \
                self.system_activity[next_tc_freq]['expiration'] > 0 and \
                self.system_activity[next_tc_freq]['tg'] not in self.lo_list:
                # Make this the traffic channel
                self.tc_freq = next_tc_freq
                # Mark it as playing
                self.system_activity[next_tc_freq].update([
                    ('playing', True),
                    ('changed', True)
                ])
                # Tune it
                self.tune_traffic_channel(self.tc_freq)
                self.next_tc_du_stats_time = time.monotonic_ns() + 500000000
                self.last_tc_stats = {}
                self.scan_state = SCANNER_PLAYING_AUDIO
                # Update the UI
                self.ui_update()
                # And we're done
                return
        # No channel tuned
        self.next_tc_du_stats_time = 0

    def update_activity(self, freq, group):
        # freq will be 0 when the superclass has not seen the IDENT_UPDATE
        # OSP (and is thus unable to convert channel to frequency). Just throw
        # away the activity; idents are sent frequently enough.
        if freq == 0:
            return

        # If the group is already active on this frequency, just re-up the
        # expiration time
        if freq in self.system_activity:
            if self.system_activity[freq]['tg'] == group:
                self.system_activity[freq].update([
                    ('expiration', time.monotonic_ns() + (self.dwell_time * 1000000))
                ])
            else:
                logging.info(f'Update for group {group} on freq {freq} without grant')
        self.scan()

    def mark_activity(self, freq, group, source):
        # freq will be 0 when the superclass has not seen the IDENT_UPDATE
        # OSP (and is thus unable to convert channel to frequency). Just throw
        # away the activity; idents are sent frequently enough.
        if freq == 0:
            return

        # First, check to see if this TG is active on a different frequency
        # and expire it immediately if so
        for known_freq in self.system_activity:
            if known_freq != freq and self.system_activity[known_freq]['tg'] == group:
                self.expire_frequency(known_freq)

        if freq in self.system_activity:
            # Use update() so as to preserve other flags/state on this frequency
            self.system_activity[freq].update([
                ('tg', group),
                ('icon', self.get_icon_for_tg(group)),
                ('description', self.get_description_for_tg(group)),
                ('source', source),
                ('expiration', time.monotonic_ns() + (self.dwell_time * 1000000)),
                ('lockout', group in self.lo_list),
                ('prio', group in self.prio_list),
                ('changed', True)
            ])
        else:
            # New frequency seen
            self.system_activity[freq] = {
                'tg': group,
                'icon': self.get_icon_for_tg(group),
                'description': self.get_description_for_tg(group),
                'source': source,
                'expiration': time.monotonic_ns() + (self.dwell_time * 1000000),
                'playing': False,
                'control_channel': group == 0 and source == 0,
                'drawer_open': False,
                'lockout': group in self.lo_list,
                'prio': group in self.prio_list,
                'changed': True
            }
        self.ui_update()
        self.scan()

    # Trunked system TSBK callbacks
    def OSP_GENERIC(self, osp):
        pass

    def OSP_RFSS_STS_BROADCAST(self, lra, active_network_connection, system_id, rfss_id, site_id, freq, service_class):
        self.mark_activity(freq, 0, 0)

    def OSP_GRP_V_CHANNEL_GRANT(self, service_opts, freq, group, source):
        self.mark_activity(freq, group, source)

    def OSP_GRP_V_CHANNEL_GRANT_UPDATE(self, freq0, group0, freq1, group1):
        self.update_activity(freq0, group0)
        self.update_activity(freq1, group1)

    def OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT(self, service_opts, freq, group, source):
        self.mark_activity(freq, group, source)

    def OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT_UPDATE(self, freq0, group0, freq1, group1):
        self.update_activity(freq0, group0)
        self.update_activity(freq1, group1)

    def handle_stats(self, port, data):
        if port == 'cc_pdus':
            if 'stats' in self.last_cc_stats:
                if data['stats']['syncs'] - self.last_cc_stats['stats']['syncs'] > 10:
                    self.broadcast_websocket_message(json.dumps({
                        'event': 'UPDATE_HEARTBEAT',
                        'display': heartbeat_sigils[self.heartbeat_counter & 1]}
                        ))
                    self.heartbeat_counter += 1
                    self.last_cc_stats = data
            else:
                self.last_cc_stats = data

            # Accumulate control channel DUID stats for quality gauge
            current_duid_stats = data['stats']['duid']
            if self.next_cc_du_stats_time == 0:
                # First time around, calculate next update time
                self.next_cc_du_stats_time = time.monotonic_ns() + 5000000000
                # Save off total CC DUs seen and total number of DUs good
                for duid in current_duid_stats:
                    self.last_cc_dus_seen += current_duid_stats[duid][0]
                    self.last_cc_dus_good += current_duid_stats[duid][1]
            elif time.monotonic_ns() > self.next_cc_du_stats_time:
                dus_seen = 0
                dus_good = 0
                for duid in current_duid_stats:
                    dus_seen += current_duid_stats[duid][0]
                    dus_good += current_duid_stats[duid][1]
                # Calculate number of CC DUs seen and number of good CC DUs seen
                # since last update time
                dus_seen_diff = dus_seen - self.last_cc_dus_seen
                dus_good_diff = dus_good - self.last_cc_dus_good
                pct = 0
                pct_frac = 0.0
                if dus_seen_diff > 0:
                    pct = min(len(quality_bars) - 1, int(dus_good_diff * 10 / dus_seen_diff)) # 0-9 based on quality
                    pct_frac = dus_good_diff / dus_seen_diff
                self.broadcast_websocket_message(json.dumps({
                    'event': 'UPDATE_CC_QUALITY',
                    'display': quality_bars[pct] + f' {pct_frac:2.1%}'
                }))
                # Save current counts for next time
                self.last_cc_dus_seen = dus_seen
                self.last_cc_dus_good = dus_good
                # Calculate next update time
                self.next_cc_du_stats_time = time.monotonic_ns() + 500000000

        # Accumulate traffic channel DUID stats
        if port == 'tc_pdus':
            current_duid_stats = data['stats']['duid']
            if len(self.last_tc_stats) == 0:
                self.last_tc_stats = current_duid_stats.copy()
            if self.next_tc_du_stats_time > 0 and time.monotonic_ns() > self.next_tc_du_stats_time:
                # Totalize current DUs seen and good counts
                dus_seen = 0
                dus_good = 0
                for duid in current_duid_stats:
                    dus_seen += current_duid_stats[duid][0]
                    dus_good += current_duid_stats[duid][1]
                # Totalize last DUs seen and good counts (from when channel
                # was changed)
                last_dus_seen = 0
                last_dus_good = 0
                for duid in self.last_tc_stats:
                    last_dus_seen += self.last_tc_stats[duid][0]
                    last_dus_good += self.last_tc_stats[duid][1]
                # Calculate number of TC DUs seen and number of good TC DUs seen
                # since last update time
                dus_seen_diff = dus_seen - last_dus_seen
                dus_good_diff = dus_good - last_dus_good
                pct = 0
                pct_frac = 0.0
                if dus_seen_diff > 0:
                    pct = min(len(quality_bars) - 1, int(dus_good_diff * 10 / dus_seen_diff)) # 0-9 based on quality
                    pct_frac = dus_good_diff / dus_seen_diff
                self.broadcast_websocket_message(json.dumps({
                    'event': 'UPDATE_TC_QUALITY',
                    'display': quality_bars[pct] + f' {pct_frac:2.1%}'
                }))
                # Calculate next update time
                self.next_tc_du_stats_time = time.monotonic_ns() + 500000000

    def voice_pcm_data(self, pcm_data):
        self.broadcast_websocket_binary_message(pcm_data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    INPUT_PORTS = ['tc_pdus', 'cc_pdus']
    OUTPUT_PORTS = ['radio_freq', 'radio_gain', 'cc_offset', 'tc_offset']
    (input_pipe, output_pipe) = Pipe()
    tui = scanner_oop_ws(INPUT_PORTS, OUTPUT_PORTS,
        input_pipe, output_pipe,
        {'site_file': '/tmp/trs_site_2_2022.csv',
         'tg_file': '/tmp/trs_tg_2_enhanced_2022.csv',
         'site_id': '1.7',
         'oop_target': 'scanner_oop_ws.scanner_oop_ws'})
    tui.main_loop()
