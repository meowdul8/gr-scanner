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

from enum import Enum
import ctypes
import logging
from multiprocessing import Process, Pipe

# Master list of TSBK OSPs
class tsbk_osps(Enum):
    # Standard OSPs (vendor ID = 0x00)
    OSP_GRP_V_CHANNEL_GRANT = (0, 0x00)
    OSP_RESERVED_01 = (1, 0x00)
    OSP_GRP_V_CHANNEL_GRANT_UPDATE = (2, 0x00)
    OSP_GRP_V_CHANNEL_GRANT_UPDATE_EXPLICIT = (3, 0x00)
    OSP_UU_V_CHANNEL_GRANT = (4, 0x00)
    OSP_UU_ANSWER_REQUEST = (5, 0x00)
    OSP_UU_V_CHANNEL_GRANT_UPDATE = (6, 0x00)
    OSP_RESERVED_07 = (7, 0x00)
    OSP_TEL_V_CHANNEL_GRANT = (8, 0x00)
    OSP_TEL_V_CHANNEL_GRANT_UPDATE = (9, 0x00)
    OSP_TEL_ANSWER_REQUEST = (10, 0x00)
    OSP_RESERVED_0B = (11, 0x00)
    OSP_RESERVED_0C = (12, 0x00)
    OSP_RESERVED_0D = (13, 0x00)
    OSP_RESERVED_0E = (14, 0x00)
    OSP_RESERVED_0F = (15, 0x00)
    OSP_INDIVIDUAL_DATA_CHANNEL_GRANT = (16, 0x00)
    OSP_GRP_DATA_CHANNEL_GRANT = (17, 0x00)
    OSP_GRP_DATA_CHANNEL_ANN = (18, 0x00)
    OSP_GRP_DATA_CHANNEL_ANN_EXPLICIT = (19, 0x00)
    OSP_SNDCP_DATA_CHANNEL_GRANT = (20, 0x00)
    OSP_SNDCP_DATA_PAGE_REQUEST = (21, 0x00)
    OSP_SNDCP_DATA_CHANNEL_ANN_EXPLICIT = (22, 0x00)
    OSP_RESERVED_17 = (23, 0x00)
    OSP_STS_UPDATE = (24, 0x00)
    OSP_RESERVED_19 = (25, 0x00)
    OSP_STS_QUERY = (26, 0x00)
    OSP_RESERVED_1B = (27, 0x00)
    OSP_MESSAGE_UPDATE = (28, 0x00)
    OSP_RADIO_UNIT_MONITOR_COMMAND = (29, 0x00)
    OSP_RESERVED_1E = (30, 0x00)
    OSP_CALL_ALERT = (31, 0x00)
    OSP_ACKNOWLEDGE_RESPONSE = (32, 0x00)
    OSP_QUEUED_RESPONSE = (33, 0x00)
    OSP_RESERVED_22 = (34, 0x00)
    OSP_RESERVED_23 = (35, 0x00)
    OSP_EXTENDED_FUNCTION_COMMAND = (36, 0x00)
    OSP_RESERVED_25 = (37, 0x00)
    OSP_RESERVED_26 = (38, 0x00)
    OSP_DENY_RESPONSE = (39, 0x00)
    OSP_GRP_AFFILIATION_RESPONSE = (40, 0x00)
    OSP_SECONDARY_CONTROL_CHANNEL_BROADCAST_EXPLICIT = (41, 0x00)
    OSP_GRP_AFFILIATION_QUERY = (42, 0x00)
    OSP_LOCATION_REG_RESPONSE = (43, 0x00)
    OSP_UNIT_REG_RESPONSE = (44, 0x00)
    OSP_UNIT_REG_COMMAND = (45, 0x00)
    OSP_AUTH_COMMAND = (46, 0x00)
    OSP_UNIT_DEREG_ACKNOWLEDGE = (47, 0x00)
    OSP_TDMA_SYNC_BROADCAST = (48, 0x00)
    OSP_AUTH_DEMAND = (49, 0x00)
    OSP_AUTH_FNE_RESPONSE = (50, 0x00)
    OSP_IDENT_UPDATE_TDMA = (51, 0x00)
    OSP_IDENT_UPDATE_VHF_UHF_BANDS = (52, 0x00)
    OSP_TIME_DATE_ANN = (53, 0x00)
    OSP_ROAMING_ADDRESS_COMMAND = (54, 0x00)
    OSP_ROAMING_ADDRESS_UPDATE = (55, 0x00)
    OSP_SYSTEM_SERVICE_BROADCAST = (56, 0x00)
    OSP_SECONDARY_CONTROL_CHANNEL_BROADCAST = (57, 0x00)
    OSP_RFSS_STS_BROADCAST = (58, 0x00)
    OSP_NETWORK_STS_BROADCAST = (59, 0x00)
    OSP_ADJACENT_STS_BROADCAST = (60, 0x00)
    OSP_IDENT_UPDATE = (61, 0x00)
    OSP_PROT_PARAMETER_BROADCAST = (62, 0x00)
    OSP_PROT_PARAMETER_UPDATE = (63, 0x00)
    # Motorola vendor-specific OSPs (vendor ID = 0x90)
    OSP_MOTOROLA_PATCH_GRP_ADD = (0, 0x90)
    OSP_MOTOROLA_PATCH_GRP_DELETE = (1, 0x90)
    OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT = (2, 0x90)
    OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT_UPDATE = (3, 0x90)
    OSP_MOTOROLA_TRAFFIC_CHANNEL_ID = (5, 0x90)
    OSP_MOTOROLA_DENY_RESPONSE = (7, 0x90)
    OSP_MOTOROLA_SYSTEM_LOADING = (9, 0x90)
    OSP_MOTOROLA_BASE_STATION_ID = (11, 0x90)
    OSP_MOTOROLA_CONTROL_CHANNEL_PLANNED_SHUTDOWN = (14, 0x90)

# Describe decoding details for each OSP
#   Key is the tsbk_osps enumeration name (string)
#   Value is a dictionary with key being the parameter name and the value
#   being how to calculate the value for the parameter
tsbk_osp_decoders = {
    'OSP_GRP_V_CHANNEL_GRANT': {
        'service_opts': [(2, 0xff, 0)],
        # If the key is a callable, it is a lambda taking the buffer of TSBK
        # payload bytes, returning the value associated with the parameter
        'freq': lambda self, data:
            self.system.channel_to_freq((data[3] << 8) | data[4]),
        # If the key is a list, it is a list of byte offsets, masks, and shifts
        # (positives are right-shifts, negatives are left-shifts) to apply,
        # with the results being bitwise ORed together
        'group': [(5, 0xff, 0), (6, 0xff, 0)],
        'source': [(7, 0xff, 0), (8, 0xff, 0), (9, 0xff, 0)]
    },
    'OSP_GRP_V_CHANNEL_GRANT_UPDATE': {
        'freq0': lambda self, data:
            self.system.channel_to_freq((data[2] << 8) | data[3]),
        'group0': [(4, 0xff, 0), (5, 0xff, 0)],
        'freq1': lambda self, data:
            self.system.channel_to_freq((data[6] << 8) | data[7]),
        'group1': [(8, 0xff, 0), (9, 0xff, 0)],
    },
    'OSP_RFSS_STS_BROADCAST': {
        'lra': [(2, 0xff, 0)],
        'active_network_connection': [(3, 0x10, 4)],
        'system_id': [(3, 0x0f, 0), (4, 0xff, 0)],
        'rfss_id': [(5, 0xff, 0)],
        'site_id': [(6, 0xff, 0)],
        'freq': lambda self, data:
            self.system.channel_to_freq((data[7] << 8) | data[8]),
        'service_class': [(9, 0xff, 0)]
    },
    'OSP_ADJACENT_STS_BROADCAST': {
        'lra': [(2, 0xff, 0)],
        'cfva': [(3, 0xf0, 4)],
        'system_id': [(3, 0x0f, 0), (4, 0xff, 0)],
        'rfss_id': [(5, 0xff, 0)],
        'site_id': [(6, 0xff, 0)],
        'freq': lambda self, data:
            self.system.channel_to_freq((data[7] << 8) | data[8]),
        'service_class': [(9, 0xff, 0)]
    },
    'OSP_SECONDARY_CONTROL_CHANNEL_BROADCAST': {
        'rfss_id': [(2, 0xff, 0)],
        'site_id': [(3, 0xff, 0)],
        'freq0': lambda self, data:
            self.system.channel_to_freq((data[4] << 8) | data[5]),
        'service_class0': [(6, 0xff, 0)],
        'freq1': lambda self, data:
            self.system.channel_to_freq((data[7] << 8) | data[8]),
        'service_class1': [(9, 0xff, 0)],
    },
    'OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT': {
        'service_opts': [(2, 0xff, 0)],
        'freq': lambda self, data:
            self.system.channel_to_freq((data[3] << 8) | data[4]),
        'group': [(5, 0xff, 0), (6, 0xff, 0)],
        'source': [(7, 0xff, 0), (8, 0xff, 0), (9, 0xff, 0)]
    },
    'OSP_MOTOROLA_PATCH_GRP_CHANNEL_GRANT_UPDATE': {
        'freq0': lambda self, data:
            self.system.channel_to_freq((data[2] << 8) | data[3]),
        'group0': [(4, 0xff, 0), (5, 0xff, 0)],
        'freq1': lambda self, data:
            self.system.channel_to_freq((data[6] << 8) | data[7]),
        'group1': [(8, 0xff, 0), (9, 0xff, 0)],
    }
}


class trunked_system():
    @staticmethod
    def parse_csv_line(line):
        in_quote = False
        fields = []
        combined_fields = []
        for part in line.split(','):
            if in_quote:
                combined_fields.append(part)
                if part[-1] == '"':
                    in_quote = False
                    fields.append(' '.join(combined_fields).strip('"'))
                    combined_fields = []
            else:
                if part[0] == '"' and part[-1] != '"':
                    in_quote = True
                    combined_fields.append(part)
                else:
                    fields.append(part)
        return fields

    def load_site_file(self, site_file):
        logging.info(f'p25_scanner: loading site file {site_file}')
        self.sites = dict()
        with open(site_file, 'r') as f:
            lines = f.read().splitlines()
            for line in lines[1:]:
                (rfss, site_dec, site_hex, site_nac, description, county, lat, lon, rng, *freqs) = line.split(',')
                site_info = {
                    'site_nac': int(site_nac, 16) if len(site_nac) > 0 else 0,
                    'description': description,
                    'county': county,
                    'latitude': float(lat),
                    'longitude': float(lon),
                    'range': float(rng),
                    'frequencies': [float(freq) * 1e6 for freq in freqs]
                }
                self.sites[(int(rfss), int(site_hex, 16))] = site_info

    def load_talkgroup_file(self, tg_file):
        logging.info(f'p25_scanner: loading talkgroup file {tg_file}')
        self.tgs = dict()
        with open(tg_file, 'r') as f:
            lines = f.read().splitlines()
            for line in lines[1:]:
                (tg_id, _, alpha_tag, mode, description, tag, category) = self.parse_csv_line(line)
                tg_info = {
                    'alpha_tag': alpha_tag.strip('"'),
                    'mode': mode,
                    'description': description.strip('"'),
                    'tag': tag,
                    'category': category
                }
                self.tgs[int(tg_id)] = tg_info

    def add_identifier(self, identifier, base, spacing):
        self.idents[identifier] = {
            'base': base,
            'spacing': spacing
        }
        # logging.info(f'p25_scanner: add identifier {identifier} (base {base}, spacing {spacing})')

    def channel_to_freq(self, channel):
        identifier = (channel & 0xf000) >> 12
        channel = (channel & 0x0fff)
        if identifier in self.idents:
            id = self.idents[identifier]
            return id['base'] + channel * id['spacing']
        else:
            return 0

    def __init__(self):
        self.sites = dict()
        self.tgs = dict()
        self.idents = dict()


class p25_scanner():
    class scanner_state(Enum):
        TUNE_RADIO = 0
        SEEK_CC = 1
        MONITOR_CC = 2

    @staticmethod
    def calculate_center_frequency(freqs):
        sorted_freqs = sorted(freqs)
        return (sorted_freqs[0] + sorted_freqs[-1]) / 2.0

    @staticmethod
    def get_du_info(du):
        is_du = 'p25_du' in du
        nac = 0
        duid = 0
        ok = False
        if is_du:
            nac = int(du['p25_du'].get('nac', 0x0), 16)
            duid = int(du['p25_du'].get('duid', 0x0), 16)
            ok = du['p25_du'].get('ok', 0) > 0
        return (is_du, nac, duid, ok)

    # Decode the OSP and dispatch to a handler if one exists
    # Note that if we get here, we know osp_name is in tsbk_osp_decoders
    def dispatch_osp(self, osp_name, osp_data):
        param_map = dict()
        # For each parameter in the decoder...
        for param_name in tsbk_osp_decoders[osp_name].keys():
            # ...determine how to get its value from osp_data
            param_value = tsbk_osp_decoders[osp_name][param_name]
            # If it's a lambda, just invoke the callable
            if callable(param_value):
                param_map[param_name] = param_value(self, osp_data)
            else:
                # Otherwise, execute the secret decoder ring
                value = 0
                for (offset, mask, shift) in param_value:
                    value <<= 8
                    partial_value = (osp_data[offset] & mask)
                    if shift > 0:
                        partial_value >>= shift
                    else:
                        partial_value <<= -shift
                    value |= partial_value
                param_map[param_name] = value
        # See if the function exists, or if OSP_GENERIC exists
        # (prefer the specific function though)
        try:
            if hasattr(self, osp_name):
                getattr(self, osp_name)(**param_map)
            elif hasattr(self, 'OSP_GENERIC'):
                getattr(self, 'OSP_GENERIC')({osp_name: param_map})
        except BaseException as e:
            logging.warning(f'p25_scanner: failed to invoke {osp_name} with {param_map}: {e}')

    def handle_tsbk(self, tsbk_buffer):
        if bool(tsbk_buffer[0] & 0x40):
            logging.info(f'p25_scanner: protected TSBK')
            return

        # Decode TSBK details and dispatch to subclass if possible
        opcode = tsbk_buffer[0] & 0x3f
        vendor = tsbk_buffer[1]

        # Identify and log the OSP if desired
        osp_name = ''
        known_osp = True
        try:
            osp = tsbk_osps((opcode, vendor))
            osp_name = osp.name
        except ValueError:
            osp_name = f'OSP_OPCODE_{opcode:02X}_VENDOR_{vendor:02X}'
            known_osp = False
        if logging.getLogger().level <= logging.DEBUG:
            osp_bytes = ' '.join([f'{byte:02x}' for byte in tsbk_buffer[2:10]])
            logging.info(f'{osp_name:<50s} {osp_bytes}')
        if not known_osp:
            return

        # Handle OSP
        # See if we know how to decode and dispatch it
        if osp_name in tsbk_osp_decoders:
            self.dispatch_osp(osp_name, tsbk_buffer)
        elif osp == tsbk_osps.OSP_IDENT_UPDATE or osp == tsbk_osps.OSP_IDENT_UPDATE_VHF_UHF_BANDS:
            identifier = (tsbk_buffer[2] & 0xf0) >> 4
            spacing = ((tsbk_buffer[4] & 0x03) << 8) | tsbk_buffer[5]
            base = (tsbk_buffer[6] << 24) | (tsbk_buffer[7] << 16) | \
                (tsbk_buffer[8] << 8) | (tsbk_buffer[9])
            self.system.add_identifier(identifier, base * 5, spacing * 125)

    def handle_stats(self, port, data):
        pass

    def do_tune_radio(self, port, data):
        # Use the first received PDU to tune the radio to the desired center
        # frequency, then go to the SEEK_CC state
        logging.info(f'p25_scanner: radio will tune to {self.radio_center_freq} Hz')
        self.send_pdu('radio_freq', {'type': 'float', 'value': self.radio_center_freq})
        self.cc_index = 0
        self.pdus_until_cc_index_change = 0
        self.state = self.scanner_state.SEEK_CC

    def do_seek_cc(self, port, data):
        # Monitor PDUs on cc_pdus looking for TSBKs or PDUs on each frequency
        # for some number of seconds at a time; if an adequate number of good
        # TSBKs or PDUs are found at that frequency, then begin monitoring it

        # Note that we only do anything when we see control channel PDUs
        if port != 'cc_pdus':
            return

        # First, set the CC channel offset to the desired frequency if it's
        # time to change frequencies
        if self.pdus_until_cc_index_change == 0:
            cc_freq = self.site_info['frequencies'][self.cc_index]
            cc_freq_offset = self.radio_center_freq - cc_freq
            logging.info(f'p25_scanner: tuning CC to {cc_freq} Hz (offset {cc_freq_offset}, freq index {self.cc_index})')
            self.send_pdu('cc_offset', {'type': 'float', 'value': cc_freq_offset})
            self.pdus_until_cc_index_change = 50
            self.good_pdus = 0
        else:
            # If it's a P25 DU, see if it's a TSBK or a PDU and if it's good
            (is_du, _, duid, du_good) = self.get_du_info(data)
            if is_du and (duid == 0x7 or duid == 0xc) and du_good:
                self.good_pdus += 1
                # If we have seen a bunch of good PDUs on the CC since the
                # last CC index change, let's assume we're on a good CC and
                # dwell here
                if self.good_pdus > 10:
                    cc_frequency = self.site_info['frequencies'][self.cc_index]
                    logging.info(f'p25_scanner: found probable CC at {self.cc_index} ({cc_frequency} Hz)')
                    self.state = self.scanner_state.MONITOR_CC
                    return
            self.pdus_until_cc_index_change -= 1
            if self.pdus_until_cc_index_change == 0:
                # Move to the next frequency in the list
                self.cc_index = (self.cc_index + 1) % len(self.site_info['frequencies'])

    def do_monitor_cc(self, port, data):
        logging.debug(f'p25_scanner: {data}')

        # Decode TSBKs
        (is_du, _, duid, du_good) = self.get_du_info(data)
        if is_du:
            # Accumulate DUID stats on control channel
            (duid_count, good_count) = self.p25_duid_stats[port].setdefault(duid, (0, 0))
            duid_count += 1
            good_count += 1 if du_good else 0
            self.p25_duid_stats[port][duid] = (duid_count, good_count)

            # TODO: Add PDU (MBT TSBK) decoding
            if duid == 0x7 and du_good:
                tsbk_buffer = bytearray.fromhex(data['p25_du'].get('tsbk', ''))
                if len(tsbk_buffer) != 12:
                    logging.warning(f'p25_scanner: TSBK detected with weird/invalid payload')
                    return
                self.handle_tsbk(tsbk_buffer)

    def do_voice_pdu(self, port, data):
        (is_du, _, duid, du_good) = self.get_du_info(data)

        if is_du:
            # Accumulate DUID stats on voice channel
            (duid_count, good_count) = self.p25_duid_stats[port].setdefault(duid, (0, 0))
            duid_count += 1
            good_count += 1 if du_good else 0
            self.p25_duid_stats[port][duid] = (duid_count, good_count)

        if is_du and (duid == 0x5 or duid == 0xa):
            imbe_frames = bytes.fromhex(data['p25_du'].get('imbe', ''))
            if self.imbe_decoder:
                for frame in range(0, 9):
                    frame_start_index = 11 * frame
                    frame_end_index = frame_start_index + 9
                    imbe_frame = imbe_frames[frame_start_index:frame_end_index]
                    self.imbe_library.imbe_decoder_decode(self.imbe_decoder, imbe_frame, self.pcm_data[frame])
                    if hasattr(self, 'voice_pcm_data'):
                        self.voice_pcm_data(self.pcm_data[frame].raw)
            else:
                logging.info(f'p25_scanner: IMBE data received, not played')


    def __init__(self, input_ports, output_ports, send_pdu_fn, params):
        logging.info('p25_scanner: instantiating')

        self.send_pdu = send_pdu_fn

        # Validate parameters
        for required_param in ['site_file', 'tg_file', 'site_id']:
            if required_param not in params:
                raise KeyError(f'p25_scanner: Required parameter \'{required_param}\' not specified')
        site_file = params['site_file']
        tg_file = params['tg_file']
        rfss_and_site = params['site_id'].split('.')
        if len(rfss_and_site) != 2:
            raise ValueError(f'p25_scanner: Site ID must be in rfss.site format')
        self.site_id = (int(rfss_and_site[0]), int(rfss_and_site[1]))

        # Validate presence of ports
        for required_input_port in ['tc_pdus', 'cc_pdus']:
            if required_input_port not in input_ports:
                raise ValueError(f'p25_scanner: Required front end input port \'{required_input_port}\' not found')
        for required_output_port in ['radio_freq', 'radio_gain', 'cc_offset', 'tc_offset']:
            if required_output_port not in output_ports:
                raise ValueError(f'p25_scanner: Required front end output port \'{required_output_port}\' not found')

        # Load IMBE decoder, if possible
        try:
            self.imbe_library = ctypes.CDLL('libimbe_vocoder.so')
            self.imbe_decoder = self.imbe_library.imbe_decoder_make()
            self.pcm_data = []
            for frame in range(0, 9):
                self.pcm_data.append(ctypes.create_string_buffer(320))
        except BaseException as e:
            logging.warning(f'p25_scanner: failed to instantiate IMBE decoder, no voice data available')
            self.imbe_decoder = None

        # Load files
        self.system = trunked_system()
        self.system.load_site_file(site_file)
        self.system.load_talkgroup_file(tg_file)

        # Configure radio for given site
        if self.site_id not in self.system.sites:
            raise ValueError(f'p25_scanner: Site ID {self.site_id} not in sites file')

        self.site_info = self.system.sites[self.site_id]
        self.radio_center_freq = self.calculate_center_frequency(self.site_info['frequencies'])

        # Each input port has its own dictionary of DUID statistics
        self.p25_duid_stats = {}
        for input_port in input_ports:
            self.p25_duid_stats[input_port] = {}

        self.state = self.scanner_state.TUNE_RADIO

    def receive_pdu(self, port, data):
        if 'stats' in data:
            data['stats'].update({'duid': self.p25_duid_stats[port]})
            self.handle_stats(port, data)
        if port == 'cc_pdus':
            [self.do_tune_radio, self.do_seek_cc, self.do_monitor_cc][self.state.value](port, data)
        elif port == 'tc_pdus':
            self.do_voice_pdu(port, data)

    def tune_traffic_channel(self, freq):
        tc_freq_offset = self.radio_center_freq - freq
        logging.info(f'p25_scanner: tuning TC to {freq} Hz (offset {tc_freq_offset})')
        self.send_pdu('tc_offset', {'type': 'float', 'value': tc_freq_offset})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    INPUT_PORTS = ['tc_pdus', 'cc_pdus']
    OUTPUT_PORTS = ['radio_freq', 'radio_gain', 'cc_offset', 'tc_offset']
    scanner = p25_scanner(INPUT_PORTS, OUTPUT_PORTS, None,
        {'site_file': '/tmp/trs_site_2_2022.csv',
         'tg_file': '/tmp/trs_tg_2_enhanced_2022.csv',
         'site_id': '1.7'})
