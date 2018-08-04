#!/usr/bin/env python3
"""
Quick IRC Chat Server

@Author: Zeke Reyna, Richard Shin

@TODO: wrap server into a class rather than a series of methods so globals and variables
can be circumvented
"""

import sys
import re
import traceback
import socket
import threading
import random
#from select import select
#import time

sys.path.append('../libs')
#from sockio import *
import sockio as sio
# --------- CONSTANTS ---------
# TIME_OUT
# TIME_OUT_QUICK
# TIME_OUT_NOTIF
# BUFF_SIZE
# --------- FUNCTIONS ---------
# try_writing_to_sock(socket, msg) @TODO: name changed to try_write(...)
# try_reading_from_sock(socket, sock_msgs, timeout=TIME_OUT) @TODO: name changed to try_read(...)
# update_msgs(socket, sock_msgs, timeout=TIME_OUT_QUICK)

# --------- CONSTANTS ---------
LISTEN_QUEUE_LIMIT = 5

from user import user
from constants import RPL_WELCOME, RPL_TOPIC, RPL_NAMREPLY, RPL_ENDOFNAMES
#from shared import killself_event, channel_newusersLock, channel_newusers, init
import shared as sh
import servlet as srv
import chitter_methods as cm

def generate_serverID():
    """
    @returns:
        server<random-num>
    """
    random.seed()
    rand = random.randint(1, 10000)
    return "server" + str(rand)

def register_session(sock, sock_msgs):
    # receive "NICK nick\r\n"
    msg = sio.try_read(sock, sock_msgs)
    nick = msg.replace("NICK ", "")

    # receive "USER user_name * * :real_name\r\n"
    msg = sio.try_read(sock, sock_msgs)
    first, second = msg.split(" * * :")
    user_name = first.replace("USER ", "")
    real_name = second

    client = user(nick, user_name, real_name)
    client.set_sock(sock)

    # send confirmation message
    # <thisIP> 001 <nick> :Welcome to the
    # Internet Relay Network <nick>!<user>@<theirIP>\r\n
    theirIP, _ = sock.getpeername()
    thisIP = socket.getfqdn()

    msg = "{} {} {} :Welcome to the ".format(thisIP,
                                             RPL_WELCOME,
                                             client.nick)
    msg += "Internet Relay Network "
    msg += "{}!{}@{}\r\n".format(client.nick,
                                 client.user_name,
                                 theirIP)
    sio.try_write(sock, msg)
    return client

def get_channel_from_client(sock, sock_msgs):
    msg = sio.try_read(sock, sock_msgs)
    channel = msg.replace("JOIN ", "")
    return channel

def server(listenPort, serverName="__NO_NAME_GIVEN__"):
    listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:

        sh.init() # call only once
        listenSocket.bind(('', listenPort))
        listenSocket.listen(LISTEN_QUEUE_LIMIT)

        # register server
        if serverName == "__NO_NAME_GIVEN__":
            serverName = generate_serverID()
        # log server to psql database
        cm.insert_server(listenSocket, serverName)

        channels__newuserevents = {} # for notifying of new users
        while True:
            sock_msgs = []
            currSock, currAddr = listenSocket.accept()
            print ("got a connection")
            client = register_session(currSock, sock_msgs)
            channel = get_channel_from_client(currSock, sock_msgs)
            client.set_channel(channel)
            print (client)
            with sh.channel_newusersLock:
                if channel in sh.channel_newusers:
                    sh.channel_newusers[channel].append((client, sock_msgs))
                else:
                    sh.channel_newusers[channel] = [(client, sock_msgs)]

            if channel in channels__newuserevents:
                channels__newuserevents[channel].set()
                continue

            channels__newuserevents[channel] = threading.Event()
            servletThread = srv.Servlet(channel,
                                        channels__newuserevents[channel],
                                        serverName)
            servletThread.setDaemon(True)
            servletThread.start()
            channels__newuserevents[channel].set()

    except Exception as e:
        if e == KeyboardInterrupt:
            print ("KeyboardInterrupt: exiting now")
        else:
            print (e)
            traceback.print_exc()
    finally:
        this_thread = threading.currentThread()
        sh.killself_event.set()
        for thread in threading.enumerate():
            if thread != this_thread:
                thread.join()
        if listenSocket:
            listenSocket.close()


if __name__ == "__main__":
    if len(sys.argv) == 2:
        print ("starting server")
        server(int(sys.argv[1]))
    elif len(sys.argv) == 3:
        print ("starting server {}".format(sys.argv[2]))
        server(int(sys.argv[1]), sys.argv[2])
    else:
        print ("Usage: python3 server.py <listen-port> [<server-name>]")
