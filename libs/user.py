#!/user/bin/env python3
"""
Simple python file for storing a user object
"""
import socket

class user:
    """
    """
    def __init__(self, nick, user_name, real_name, password='', channel=''):
        self.nick      = nick
        self.user_name = user_name
        self.real_name = real_name
        self.password  = password
        self.channel   = channel

    def __str__(self):
        to_user = "nick: " + self.nick + "\n" + \
                "user: " + self.user_name + "\n" + \
                "real_name: " + self.real_name + "\n" + \
                "password: " + self.password + "\n" + \
                "channel: " + self.channel
        return to_user

    def set_sock(self, socket):
        self.socket = socket

    def set_nick(self, nick):
        self.nick     = nick

    def set_pass(self, password):
        self.password = password

    def set_channel(self, channel):
        self.channel  = channel

