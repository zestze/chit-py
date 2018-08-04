#!/usr/bin/env python3
"""
Module for a 'channel'
"""

import sys
import re
import threading
import socket
import traceback
import random

sys.path.append('../libs')
import sockio as sio
# --------- CONSTANTS ---------
# TIME_OUT
# TIME_OUT_QUICK
# TIME_OUT_NOTIF
# BUFF_SIZE
# --------- FUNCTIONS ---------
# try_writing_to_sock(socket, msg) @TODO: name changed to sio.try_write(...)
# try_reading_from_sock(socket, sock_msgs, timeout=TIME_OUT) @TODO: name changed to try_read(...)
# update_msgs(socket, sock_msgs, timeout=TIME_OUT_QUICK)

from user import user
from constants import RPL_WELCOME, RPL_TOPIC, RPL_NAMREPLY, RPL_ENDOFNAMES
#from shared import killself_event, channel_newusers, channel_newusersLock, init
import shared as sh
import chitter_methods as cm

class Servlet(threading.Thread):
    """
    thread for hosting a channel
    """
    def __init__(self, channel_name, notify_of_newusers,
                serverName):
        """Constructor"""
        threading.Thread.__init__(self)
        self.channel_name = channel_name
        self.notify_of_newusers = notify_of_newusers
        self.users = {}
        self.topic = "DEFAULT TOPIC"
        self.mul_sock_msgs = {} # key, value: socket, msgs
        self.serverName = serverName
        self.channelID = ""

    def set_topic(self, t):
        self.topic = t

    def login_psql_db(self):
        """ For Initial Login to DB"""
        random.seed()
        rand = random.randint(1, 10000)
        channelID = "channel" + str(rand)
        self.channelID = channelID
        cm.insert_channel(channelID, self.channel_name,
                          self.topic, self.serverName)

    def run(self):
        """main"""
        try:
            self.login_psql_db()
            # log channel into databse
            while not sh.killself_event.is_set():
                if self.notify_of_newusers.is_set():
                    self.handle_new_users()

                # @NOTE: this is only for the update... call
                # and considering the dict getting passed already has
                # the sockets carried with it, don't really need to
                # do this
                client_socks = []
                for _, usr in self.users.items():
                    client_socks.append(usr.socket)

                #read_socks = sio.update_mul_sock_msgs()
                # @TODO: left off here, not sure how to incorporate mul_sock_msgs
                socks_to_handle = sio.update_mul_sock_msgs(client_socks, self.mul_sock_msgs)

                for sock in socks_to_handle:
                    for msg in self.mul_sock_msgs[sock]:
                        self.handle_msg(sock, msg)
                    if sock in self.mul_sock_msgs: # in case user left and socket was destroyed
                        self.mul_sock_msgs[sock][:] = []

                # @TODO: check if all users have left, and if so, break loop?

                if len(self.users.items()) == 0:
                    print ("All users left, Channel closing")
                    print ("Channel ID: {} Channel Name: {}".format(self.channelID,
                                                                    self.channel_name))
                    break

        except Exception as e:
            print (e)
            traceback.print_exc()
        finally:
            for u in self.users.values():
                if u.socket:
                    u.socket.close()

    def handle_msg(self, sock, msg):
        from_user = None # nick of user who sent msg
        for usr_nick, usr in self.users.items():
            if sock == usr.socket:
                from_user = usr_nick
                break

        if msg[:7] == "PRIVMSG":
            # :<nick>!<usser>@<user-ip> PRIVMSG <channel> :<msg>
            # PRIVMSG <channel> :<msg>
            theirIP, _ = self.users[from_user].socket.getpeername()
            reply = ":{}!{}@{} {}\r\n".format(from_user,
                                              self.users[from_user].user_name,
                                              theirIP,
                                              msg)
            for usr_nick, usr in self.users.items():
                if usr_nick == from_user:
                    continue
                else:
                    sio.try_write(usr.socket, reply)

            # log msg into database because we're facebook
            cm.insert_msg(self.channelID, self.users[from_user], msg, self.serverName)

        elif msg[:4] == "PART":
            # :<nick>!<user>@<user-ip> PART <channel>
            # PART <channel>
            theirIP, _ = self.users[from_user].socket.getpeername()
            reply = ":{}!{}@{} {}\r\n".format(from_user,
                                              self.users[from_user].user_name,
                                              theirIP,
                                              msg)
            for usr_nick, usr in self.users.items():
                if usr_nick == from_user:
                    continue
                else:
                    sio.try_write(usr.socket, reply)

            if self.users[from_user].socket:
                self.users[from_user].socket.close()
            del self.mul_sock_msgs[self.users[from_user].socket]
            del self.users[from_user]

        else:
            print ("unrecognized message:")
            print (msg)

    def handle_new_users(self):
        client = None
        newusers__sockmsgs_list = []
        with sh.channel_newusersLock:
            newusers__sockmsgs_list = sh.channel_newusers[self.channel_name]
            sh.channel_newusers[self.channel_name] = []
        self.notify_of_newusers.clear()

        for newu, their_sockmsgs in newusers__sockmsgs_list:
            # copy over user and their sock_msgs
            self.users[newu.nick] = newu
            self.mul_sock_msgs[newu.socket] = their_sockmsgs
            theirIP, _ = newu.socket.getpeername()
            msg = "{}!{}@{} ".format(newu.nick,
                                     newu.user_name,
                                     theirIP)
            msg += "JOIN {}\r\n".format(self.channel_name)

            usernames = ""
            for _, usr in self.users.items():
                sio.try_write(usr.socket, msg)
                usernames += "@" + usr.nick + " "

            thisIP = socket.getfqdn()
            msg = "{} {} ".format(thisIP, RPL_TOPIC)
            msg += "{} {} :{}\r\n".format(newu.nick, self.channel_name, self.topic)
            sio.try_write(newu.socket, msg)

            msg = "{} {} ".format(thisIP, RPL_NAMREPLY)
            msg += "{} {} :{}\r\n".format(newu.nick, self.channel_name, usernames)
            sio.try_write(newu.socket, msg)

            msg = "{} {} ".format(thisIP, RPL_ENDOFNAMES)
            msg += "{} {} :End of NAMES list\r\n".format(newu.nick, self.channel_name)
            sio.try_write(newu.socket, msg)

            # if this is the first user to register, make them admin
            if len(self.users.items()) == 1:
                cm.insert_per_ch_user_stat(self.channelID, newu, cm.Status.Admin,
                                           self.serverName)
            else:
                cm.insert_per_ch_user_stat(self.channelID, newu, cm.Status.User,
                                           self.serverName)


