#!/usr/bin/env python3
"""
Simple 'library'-like python file for
simplifying socket operations
"""

# --------- CONSTANTS ----------
TIME_OUT       = 20
TIME_OUT_QUICK = 1
TIME_OUT_NOTIF = "__time-out__"
BUFF_SIZE      = 1028
# --------- CONSTANTS ----------

import socket
#import select
from select import select
import time

#def try_writing_to_sock(socket, msg):
def try_write(socket, msg):
    """
    @param: msg is expected to be a string
    """
    # every msg must end with '\r\n'
    # and have exactly one '\r\n'
    if msg[-2:] != "\r\n":
        to_user = repr("\r\n")
        to_user = " not in msg"
        raise Exception(to_user)

    _, writeable_socks, _ = select([], [socket], [], TIME_OUT)
    if not writeable_socks:
        return TIME_OUT_NOTIF
    socket.send(msg.encode("ascii"))

#def try_reading_from_sock(socket, sock_msgs, timeout=TIME_OUT):
def try_read(socket, sock_msgs, timeout=TIME_OUT):
    """
    @param: sock_msgs is a list that holds all the msgs for a given socket
                will be modified to hold additional msgs after call

    meant to be used when you are expecting a response, synchronously,
    for some event or action.

    thus, a time out needs to be handled, and the time out needs to be large.

    @returns: the first msg to be handled from this socket, or a notif saying socket
    timed out
    """
    if sock_msgs:
        return sock_msgs.pop(0)

    readable_socks, _, _ = select([socket], [], [], timeout)
    if not readable_socks:
        return TIME_OUT_NOTIF

    full_msg = ""
    while len(full_msg) == 0:
        full_msg = socket.recv(BUFF_SIZE).decode()
    msgs = [msg for msg in full_msg.split("\r\n") if msg != ""]
    sock_msgs.extend(msgs)
    return sock_msgs.pop(0)

def update_sock_msgs(socket, sock_msgs, timeout=TIME_OUT_QUICK):
    """
    @param: sock_msgs is a list that holds all the msgs for a given socket
            will be modified to hold additional msgs after call

    meant to be used when polling for a message.

    @returns: true if socket is read from, false, if not read from
    """
    readable_socks, _, _ = select([socket], [], [], timeout)
    if readable_socks:
        full_msg = socket.recv(BUFF_SIZE).decode()
        msgs = full_msg.split("\r\n")
        msgs = [msg for msg in msgs if msg != ""]
        sock_msgs.extend(msgs)
        return True
    return False

def update_mul_sock_msgs(sockets, mul_sock_msgs, timeout=TIME_OUT_QUICK):
    """
    for use in servlet, when multiple sockets exist

    @param: mul_sock_msgs is a dict that holds lists of all msgs read for
        each socket waiting to be processed

    @returns: a list of the sockets that correspond to the msgs lists that
        have msgs needing to be processed
    """
    readable_socks, _, _ = select(sockets, [], [], timeout)
    if readable_socks:
        for sock in readable_socks:
            full_msg = sock.recv(BUFF_SIZE).decode()
            msgs = full_msg.split("\r\n")
            msgs = [msg for msg in msgs if msg != ""]
            mul_sock_msgs[sock].extend(msgs)

    socks_with_content = []
    for sock, sock_msgs in mul_sock_msgs.items():
        if len(sock_msgs) > 0:
            socks_with_content.append(sock)
    return socks_with_content
