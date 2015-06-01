import sys
import serial
import serial.tools.list_ports
import colorama


def get_ports():
    if sys.platform.startswith('win32'):
        com_ports = [(name, desc.encode('utf-16-be').decode('cp1251'), v_p)
                     for name, desc, v_p
                     in serial.tools.list_ports.comports()]
    else:
        raise NotImplementedError('Add functionality for other than win32 systems')
    s_cp = sorted(com_ports, key=lambda tup: tup[0])
    for num, port in enumerate(s_cp):
        print('{0} - PORT: {1[0]}, DESCRIPTION: {1[1]}'.format(num, port))

    return s_cp


def select_port(cp_list):
    num = int(input('Which port do you want to select?: '))
    return cp_list[num][0]


class SerCom:
    """
    This is the wrapper class for pyserial API

    @__init__ : Accepts a port name.
    Must do a check for correct input like '/dev/tty' for Linux, 'COM' for Windows and so on

    @open_port: Do opening of the port

    @close_port: Do closing of the port

    @send_command(command): Pass the string you want to be sent to the port.
    At the end of the command adds _RETEND bytestring
    """

    _RETEND = b'\r\n'

    def __init__(self, port):
        self.port = port
        self.ser = None

    def open_port(self, baud=115200):
        try:
            self.ser = serial.Serial(self.port, baud)
            print("Port %s is opened now at baud %s" % (self.port, baud))
        except serial.SerialException:
            print("Device on port %s is busy or not found" % self.port)
            sys.exit()

    def close_port(self):
        if self.ser.isOpen():
            self.ser.close()
            print("The port is succesfully closed" if not self.ser.isOpen() else "Can not close the port")
        else:
            print("Port was not opened")

    def send_command(self, command):
        b_com = command.encode('utf-8') + self._RETEND
        self.ser.write(b_com)


class SwarmNode(SerCom):
    CUR_FILE = r'D:\PVE\Utilities\cur.txt'
    __rato_buf = []
    __rrn_buf = []
    __buffer = []
    __COMMANDS = {
        'RATO_WO_TO': 'RATO 0 ',
        'RATO_W_TO': 'RATO 1 ',
        'GET_SET': 'GSET',
        'RES_SET': 'RSET',
        'SAVE_SET': 'SSET',
        'GET_ID': 'GNID'
    }

    __OUT_LEN = {
        'RATO': 3,
        'RRN': 6
    }

    __NOTIF = ['RRN', 'NIN', 'AIR', 'SDAT', 'DNO']

    def __init__(self, port, disp_dist=False, disp_rrn=False):
        SerCom.__init__(self, port)
        self.disp_dist = disp_dist
        self.dist_rrn = disp_rrn

    def ranging(self, addr):
        if type(addr) != str:
            raise TypeError
        
        self.send_command(self.__COMMANDS['RATO_WO_TO'] + addr)
    
    def get_nodeid(self):
        self.send_command(self.__COMMANDS['GET_ID'])
        return self.get_resp_u()

    def get_settings(self):
        self.send_command(self.__COMMANDS['GET_SET'])
        return self.get_resp_u()

    def get_swarm_data(self):
        while True:
            try:
                msg = self.get_resp_u()
                self.__buffer.append(msg)
            except serial.SerialException:
                return

    def get_resp_b(self):
        c = self.ser.read()
        data = []
        if c == b'=' or c == b'*':
            data = self.ser.readline()
        else:
            nlines = int(self.ser.readline())
            for i in range(nlines):
                data.append(self.ser.readline())
            c += bytes(str(nlines).encode('utf-8')) + self._RETEND
            data = b''.join(data)
        return c + data

    def get_resp_u(self):
        return self.get_resp_b().decode('utf-8')

    def __split_buf_msg(self, buf, msg_len):
        split_msg = []
        num_val = len(buf)
        if not num_val == 0:
            for msg in buf:
                msg = msg.split(',')
                if not len(msg) == msg_len:
                    continue
                split_msg.append(msg)
            
            return split_msg
        else:
            return -1

    def __process_rato(self):
        dist = 0
        t_buf = self.__split_buf_msg(self.__rato_buf, self.__OUT_LEN['RATO'])
        sz = len(t_buf)
        if not sz == 0:
            for err, d, rssi in iter(t_buf):
                if not err[-1] == 0:
                    sz -= 1
                    continue
                dist += int(d) / 100

        dist = dist / sz if not sz == 0 else 0

        return dist

    def __process_rrn(self):
        dist = 0
        t_buf = self.__split_buf_msg(self.__rato_buf, self.__OUT_LEN['RRN'])
        sz = len(t_buf)
        if not sz == 0:
            for *addr, err, d, ncfg, ncfgd in iter(t_buf):
                if not err == '0':
                    sz -= 1
                    continue
                dist += int(d) / 100

        dist = dist / sz if not sz == 0 else 0

        return dist

    def process_buf(self, out):
        t_buf = self.__buffer[:]

        for i in range(len(t_buf)):
            if any(n in t_buf[i] for n in self.__NOTIF):
                self.__rrn_buf.append(self.__buffer[i])
            else:
                self.__rato_buf.append(self.__buffer[i])

        self.__buffer.clear()
        
        for item in self.__rato_buf:
            out.write(item)

        if self.disp_dist:
            rato_dist = self.__process_rato()
            rrn_dist = self.__process_rrn()

            out_str = colorama.Style.BRIGHT + colorama.Fore.CYAN + \
                "Current distance (RATO): {:>5.2f} m".format(rato_dist) + " " + \
                "Current distance (RRN): {:>5.2f} m".format(rrn_dist) + colorama.Style.RESET_ALL
            print(out_str, end='\r')
            print(out_str, file=self.CUR_FILE)

        self.__rato_buf.clear()
        self.__rrn_buf.clear()

        out.flush()
