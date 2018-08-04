#!/usr/bin/env python3
import sqlalchemy as sql
import socket
import datetime
import pytz
import geocoder
import enum

import user

DATABASEURI = "postgresql://eer2138:columbiacrusheshalloffame@35.227.79.146/proj1part2"
engine = sql.create_engine(DATABASEURI)


class Status(enum.Enum):
    """
    Enum for limiting status's that can be passed to the DB
    """
    def __str__(self):
        return str(self.value)
    Admin  = "Admin"
    User   = "User"
    Banned = "Banned"

def get_local_ip():
    """
    @returns:
        machine's local ip
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    ip, _ = sock.getsockname()
    sock.close()
    return ip

def insert_user(client):
    """
    @params:
        @client is of type user

    @returns:
        if user is brand new: True
        if user is old, password incorrect: False, <correct-password>
        if user is old, password correct: True

    """
    conn = engine.connect()

    query_str = 'SELECT * FROM "User";'
    cursor = conn.execute(query_str)
    for row in cursor:
        if client.real_name == row[0]:
            password = row[3]
            cursor.close()
            if password != client.password:
                return False, password
            else:
                return True, "_throw_away_text_"

    cursor = conn.execute("""INSERT INTO "User" (userid, loginname, password)
                          VALUES (%s, %s, %s);""", (client.real_name,
                                                    client.nick,
                                                    client.password))
    cursor.close()
    return True, "_throw_away_text_"

def update_bio(client, bio):
    """
    @params:
        @client is of type user
        @bio is a string

    @returns:
        nothing
    """
    conn = engine.connect()

    cursor = conn.execute("""UPDATE "User" SET bio = %s
                          WHERE userid = %s;""", (bio, client.real_name))
    cursor.close()

def insert_login(sock, user):
    """
    @params:
        @sock: socket connected to IRC server
        @user: client's user object
    """
    now = datetime.datetime.now(pytz.utc)
    ip, port = sock.getsockname()
    # this gives an internal ip... so need to make a phony connection
    # to get actual ip
    ip = get_local_ip()
    lat, lon = geocoder.ip("me").latlng

    conn = engine.connect()

    cursor = conn.execute("""INSERT INTO "LoginInstance" (ip, port, datetime, latitude,
                          longitude, userid)
                          VALUES (%s, %s, %s, %s, %s, %s);""", (ip, port,
                                                               now,
                                                               lat, lon,
                                                               user.real_name))
    cursor.close()

def insert_server(sock, serverID):
    """
    @params:
        @sock: socket server using to listen
        @serverID: server name, randomly generated
    """
    # @TODO: need to check if serverID exists, just in case
    # to be robust

    # @TODO: idea: instead of randomly generating worthless serverID,
    # require cLI args for a server name

    ip, port = sock.getsockname()
    # this gives an internal ip... so need to make a phony connection
    # to get actual ip
    ip = get_local_ip()
    lat, lon = geocoder.ip("me").latlng

    conn = engine.connect()

    cursor = conn.execute("""INSERT INTO "Server" (servername, ip, port,
                          latitude, longitude)
                          VALUES (%s, %s, %s, %s, %s);""", (serverID,
                                                            ip, port,
                                                            lat, lon))
    cursor.close()

def insert_channel(channelID, channel_name, channel_topic, serverName):
    """
    @params:
        @channelID: channel<randint>
    """
    # @TODO: need to check if serverID exists, just in case
    # to be robust
    conn = engine.connect()

    # @TODO: need to limit serverName and channel_name to make sure it's not too long
    cursor = conn.execute("""INSERT INTO "Channel" (channelID, channelname,
                          channeltopic, servername)
                          VALUES (%s, %s, %s, %s);""", (channelID,
                                                        channel_name,
                                                        channel_topic,
                                                        serverName))
    cursor.close()

def insert_msg(channelID, client, msg, serverName):
    """
    @params:
        @channelid: a unique ID identifying this specific channel
        @client: of type user, the one sending the msg
        @msg: the message being broadcasted across the server
        @serverName: the unique serverName identifying the server
    """
    conn = engine.connect()

    now = datetime.datetime.now(pytz.utc)

    # get rid of extra info preceding msg
    # PRIVMSG <#channel> :<msg>
    msg = msg[msg.find(":") + 1:]

    # make sure msg is under 100 characters, and if over, put suffix to signify so
    # this is no longer necessary, singe database column got changed to TEXT
    #if len(msg) > 100:
        #msg = msg[:100 - 3] + "..."

    cursor = conn.execute("""INSERT INTO "Msg" (channelid, userid, datetime, msg, servername)
                          VALUES (%s, %s, %s, %s, %s);""", (channelID,
                                                           client.real_name,
                                                           now,
                                                           msg,
                                                           serverName))
    cursor.close()

def insert_per_ch_user_stat(channelID, client, status_enum, serverName):
    """
    @params:
        @channelid: unique ID identifying channel
        @client: of type user, the user currently registering
        @status_enum: ('Admin', 'User', 'Banned')
        @servername: the unique string identifying the server
    """
    conn = engine.connect()

    # @TODO: set so that a SELECT is done to check if user is already there.
    # in case they login again. Else this will all crash since the primary key

    cursor = conn.execute("""INSERT INTO "Per_Ch_User_Stat" (userid, channelid, status,
                          displayname, servername)
                          VALUES (%s, %s, %s, %s, %s);""", (client.real_name,
                                                            channelID,
                                                            str(status_enum),
                                                            client.nick,
                                                            serverName))
    cursor.close()

class FriendResultCode(enum.Enum):
    FriendDontExist = 1
    AlreadyFriends = 2
    Successful = 3

def insert_friend(client, theirFriendsRealName):
    """
    @params:
        @client: of type user, the user currently using the client
        @theirFriendsID: the user.real_name of the friend they're adding

    @returns:
        False, if friendship already exists
        True, if friendship was created
    """
    conn = engine.connect()

    cursor = conn.execute("""SELECT DISTINCT userid from "User";""")
    friend_exists = False
    for row in cursor:
        if row[0] == theirFriendsRealName:
            friend_exists = True
            break

    if not friend_exists:
        return FriendResultCode.FriendDontExist


    cursor = conn.execute("""SELECT friend1id, friend2id from "Friend";""")
    for f1id, f2id in cursor:
        if f1id == client.real_name and f2id == theirFriendsRealName:
            return FriendResultCode.AlreadyFriends
        if f1id == theirFriendsRealName and f2id == client.real_name:
            return FriendResultCode.AlreadyFriends

    cursor = conn.execute("""INSERT INTO "Friend" (friend1id, friend2id)
                          VALUES (%s, %s);""", (client.real_name,
                                                theirFriendsRealName))
    cursor.close()
    return FriendResultCode.Successful

def fetch_friends(client):
    """
    @params:
        @client: of type user, the user currently using the client

    @returns:
        list of this client's friends
    """
    # @TODO: everything lol
    conn = engine.connect()

    cursor = conn.execute("""SELECT DISTINCT friend2id from "Friend"
                          WHERE friend1id=%s;""", (client.real_name))
    friends = []
    for row in cursor:
        friends.append(row[0])

    return friends
