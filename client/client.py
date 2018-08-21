#!/usr/bin/env python3
"""
Quick IRC Chat Client

@Author: Zeke Reyna, Richard Shin

@NOTE: getpass and termcolor will only work on linux

@TODO: not sure why the 'host 8080' is getting printed
"""
import sys
import re
import getpass
import traceback
import socket
from termcolor import colored, cprint # @NOTE: this will only work on linux
from enum import Enum

sys.path.append('../libs')
#from sockio import *
import sockio as sio
# --------- CONSTANTS ---------
# TIME_OUT
# TIME_OUT_QUICK
# TIME_OUT_NOTIF
# BUFF_SIZE
# --------- FUNCTIONS ---------
# try_write(socket, msg)
# try_read(socket, sock_msgs, timeout=TIME_OUT)
# update_msgs(socket, sock_msgs, timeout=TIME_OUT_QUICK)

from user import user
from constants import RPL_WELCOME, RPL_TOPIC, RPL_NAMREPLY, RPL_ENDOFNAMES
import chitter_methods as cm

RESERVED_CHARS = [":", "!", "@", " ", "\t", "\n"]

class Code(Enum):
    """
    For determining if client should quit, leave, or stay in main loop
    """
    QUIT  = 1
    LEAVE = 2
    STAY  = 3

def to_cyan(msg):
    return colored(msg, "cyan", attrs=["bold"])

def query_for():
    """
    Query user for rel. info, put info into an instance of user
    """
    msg = "\n#############################\n" \
            "Going to ask for user info...\n" \
            "Note: these are reserved characters that cannot be used:"
    msg += repr(' '.join(RESERVED_CHARS)) + "\n\n"
    msg += "What nickname would you like?"
    print (to_cyan(msg))
    nick_name = input("")

    user_name = getpass.getuser() # @NOTE: won't work on Mac

    msg = "\nWhat is your real name?"
    print (to_cyan(msg))
    real_name = input("")

    # @TODO: add passsword support in the future
    #msg = "NOTE: ignoring passwords in this impl.\n"
    msg = "\nWhat is your password?"
    print (to_cyan(msg))
    password = input("")
    return user(nick_name, user_name, real_name, password)

def connect_to_server(server_ip, server_port):
    """
    binds to any available address or port
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(('', 0))
    server_sock.connect((server_ip, server_port))
    return server_sock

def pass_user_to_server(user, socket, sock_msgs):
    """
    @TODO: passwords
    """
    msg = "NICK {}\r\n".format(user.nick)
    sio.try_write(socket, msg)
    msg = "USER {} * * :{}\r\n".format(user.whoami,
                                       user.real_name)
    sio.try_write(socket, msg)
    reply = sio.try_read(socket, sock_msgs)
    while reply == sio.TIME_OUT_NOTIF:
        reply = sio.try_read(socket, sock_msgs)

def connect_to_channel(user, socket, sock_msgs):
    """
    """
    msg = "\n#############################\n" \
            "What #channel would you like to join?"
    print (to_cyan(msg))
    channel = input("")
    if channel[0] != "#":
        channel = "#" + channel
    user.set_channel(channel)
    msg = "JOIN {}\r\n".format(channel)
    sio.try_write(socket, msg)

    # wait for confirmation message from server
    reply = sio.try_read(socket, sock_msgs)
    while reply == sio.TIME_OUT_NOTIF:
        reply = sio.try_read(socket, sock_msgs)
    msg = "\n#############################\n" \
            "Successfully connected to {}".format(channel)
    print (to_cyan(msg))

    # should get a TOPIC
    reply = sio.try_read(socket, sock_msgs)
    while reply == sio.TIME_OUT_NOTIF:
        reply = sio.try_read(socket, sock_msgs)

    msg = "\n#############################\n" \
            "{} Topic:\n".format(channel)
    msg += parse_topic(reply)
    print (to_cyan(msg))

    # should get LIST of users
    reply = sio.try_read(socket, sock_msgs)
    while reply == sio.TIME_OUT_NOTIF:
        reply = sio.try_read(socket, sock_msgs)

    msg = "\n#############################\n" \
            "{} Users:\n".format(channel)
    msg += parse_user_list(reply)
    print (to_cyan(msg))

    # should get END OF NAMES
    reply = sio.try_read(socket, sock_msgs)
    while reply == sio.TIME_OUT_NOTIF:
        reply = sio.try_read(socket, sock_msgs)
    return channel

def parse_topic(msg):
    """
    format:
        <this-ip> RPL_TOPIC <nick> <#channel> :<topic-description>
    """
    _, topic = msg.split(":", 1)
    return topic

def parse_user_list(msg):
    """
    format:
        <this-ip> RPL_NAMREPLY <nick> <#channel> :<@user1 @user2 ... >
    """
    _, users = msg.split(":", 1)
    return users

def parse_privmsg(msg):
    """
    :<nick>!<user>@<user-ip> PRIVMSG <channel> :<msg>
    """
    info, priv_msg = [x for x in msg.split(":", 2) if x != ""]
    nick = re.match("\w+!", info).group(0).replace("!", "")
    return nick, priv_msg

def parse_partmsg(msg):
    """
    :<nick>!<user>@<user-ip> PART <channel> [:<parting-msg>]
    """
    nick = re.match(":\w+!", msg).group(0).replace(":", "").replace("!", "")
    _, channel = msg.split("PART ", 1)
    return nick, channel

def parse_joinmsg(msg):
    """
    <nick>!<user>@<user-ip> JOIN <channel>
    """
    new_user_temp, channel = msg.split(" JOIN ")
    nick, _ = new_user_temp.split("!")
    return nick, channel

def parse_msg(msg):
    """
    """
    if "PRIVMSG" in msg:
        nick, priv_msg = parse_privmsg(msg)
        print ("{}: {}".format(nick, priv_msg))
    elif "PART" in msg:
        nick, channel  = parse_partmsg(msg)
        print ("{} LEFT CHANNEL {}".format(nick, channel))
    elif "JOIN" in msg:
        nick, channel = parse_joinmsg(msg)
        print ("{} JOINED CHANNEL {}".format(nick, channel))
    else:
        print (msg)
        print ("error, unrecognized message")

def handle_user_input(user, msg, socket):
    """
    """
    if msg == "":
        return Code.STAY
    elif msg == "EXIT":
        part_msg = "PART {}\r\n".format(user.channel)
        sio.try_write(socket, part_msg)
        socket.close()
        return Code.QUIT
    elif msg == "HELP":
        to_user = "options...\n" + \
                "EXIT: exit the client\n" + \
                "HELP: print this dialog\n"
        print (to_cyan(to_user))
        return Code.STAY
    else:
        priv_msg = "PRIVMSG {} :{}\r\n".format(user.channel, msg)
        sio.try_write(socket, priv_msg)
        return Code.STAY

def bio_feature(this_user):
    """
    @params:
        @this_user:

    @returns:
        True, if should continue
        False, if should quit
    """
    msg = "\n#############################\n" \
            "Would you like to add / change your bio? YES or NO"
    print (to_cyan(msg))
    reply = input("")
    while reply not in ("YES", "NO"):
        print (to_cyan(msg))
        reply = input("")

    if reply == "NO":
        return True

    msg = "\n#############################\n" \
            "Please type your bio below:"
    print (to_cyan(msg))
    reply = input("")

    cm.update_bio(this_user, reply)
    return False

def friends_feature(this_user):
    """
    @params:
        @this_user:

    @returns:
        True, if should continue
        False, if should quit
    """
    msg = "\n#############################\n" \
            "Would you like to view/add friends? YES or NO"
    print (to_cyan(msg))
    reply = input("")
    while reply not in ("YES", "NO"):
        print (to_cyan(msg))
        reply = input("")

    if reply == "NO":
        return True

    msg = "\n#############################\n" \
            "Would you like to view or add friends? VIEW or ADD"
    print (to_cyan(msg))
    reply = input("")
    while reply not in ("VIEW", "ADD"):
        print (to_cyan(msg))
        reply = input("")

    if reply == "VIEW":
        friends = cm.fetch_friends(this_user)
        msg = "\n#############################\n" \
                "Here is a list of your friends:"
        for friend in friends:
            msg += "\n" + friend

        print (to_cyan(msg))

    elif reply == "ADD":
        msg = "\n#############################\n" \
                "Please type the real_name of the person you'd like to add:"
        print (to_cyan(msg))
        reply = input("")
        friendResultCode = cm.insert_friend(this_user, reply)
        if friendResultCode == cm.FriendResultCode.AlreadyFriends:
            msg = "\n#############################\n" \
                    + reply + " is already your friend"
            print (to_cyan(msg))
        elif friendResultCode == cm.FriendResultCode.FriendDontExist:
            msg = "\n#############################\n" \
                    + reply + " doesn't exist"
            print (to_cyan(msg))
        elif friendResultCode == cm.FriendResultCode.Successful:
            msg = "\n#############################\n" \
                    + reply + " is now your friend!"
            print (to_cyan(msg))

    return False


def client(server_ip, server_port):
    """
    Main entry point for program
    """
    serv_sock = None
    try:
        sock_msgs = []
        this_user = query_for()
        if cm.check_user_exists(this_user.nick):
            if not cm.verify_password(this_user.nick, this_user.password):
                to_user = "Incorrect Password. Please try Again."
                print (to_cyan(to_user))
                return
        else:
            cm.insert_user(this_user)

        if not bio_feature(this_user):
            print (to_cyan("quitting..."))
            return

        if not friends_feature(this_user):
            print (to_cyan("quitting..."))
            return

        serv_sock = connect_to_server(server_ip, int(server_port))
        cm.insert_login(serv_sock, this_user.nick)
        pass_user_to_server(this_user, serv_sock, sock_msgs)
        connect_to_channel(this_user, serv_sock, sock_msgs)


        msg = "\n#############################\n" \
                "Type and press <ENTER> to send a message\n" \
                "Type EXIT and press <ENTER> to leave the channel\n" \
                "$EXIT<ENTER>\n" \
                "Type HELP and press <ENTER> to find out more\n" \
                "$HELP<ENTER>\n" \
                "Have fun :)"
        print (to_cyan(msg))

        code = Code.STAY
        while code != Code.QUIT:
            sio.update_sock_msgs(serv_sock, sock_msgs)
            for msg in sock_msgs:
                parse_msg(msg)
            del sock_msgs[:]

            msg = input(colored("{}: ".format(this_user.nick), "cyan", attrs=["bold"]))
            code = handle_user_input(this_user, msg, serv_sock)
    except Exception as e:
        print (e)
        traceback.print_exc()
    finally:
        if serv_sock:
            serv_sock.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print ("Usage: python3 client.py <server-ip> <server-port>")
    else:
        print ("Starting client...")
        client(sys.argv[1], sys.argv[2])
