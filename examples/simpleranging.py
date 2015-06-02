# coding: utf-8

__author__ = 'pve'

import sys
import swarm
import time
import sched
import threading
import colorama

SW_ADDR = '00006A0F3FFC'
RATO_FILE = r'D:\PVE\Utilities\rato.txt'


def sched_range(sw_node, addr, intvl):
    sw_node.ranging(addr)
    s.enter(intvl, 1, sched_range, (sw_node, addr, intvl))


def proc_buf(swarm_node, out):
    swarm_node.process_buf(out)
    s.enter(1, 2, proc_buf, (swarm_node, out))


av_p = swarm.get_ports()
num_p = int(input('Which port do you want to open?: '))
output = open(RATO_FILE, 'w')

colorama.init()
sc = swarm.SwarmNode(swarm.num_to_portname(av_p, num_p), disp_dist=True, disp_rrn=True)
sc.open_port()

intv = float(input('Enter the interval between ranging: '))
s = sched.scheduler(time.time, time.sleep)
sw_getmsg = threading.Thread(target=sc.get_swarm_data)
s.enter(intv, 1, sched_range, (sc, SW_ADDR, intv))
s.enter(1, 2, proc_buf, (sc, output))

try:
    sw_getmsg.start()
    s.run()
except KeyboardInterrupt:
    print()
    print('Keyboard interrupt. Stopping...')
except:
    print('Unexpected error: ', sys.exc_info()[0])
    raise
finally:
    if sc:
        sc.close_port()
    if output:
        output.close()
