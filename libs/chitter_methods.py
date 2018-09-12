#!/usr/bin/env python3
"""
@TODO: need more secure way of doing database manipulation.
        move all database stuff to server-side, and let it do it there based on configs?
        since rn anyone can get the data i give em and wreak havoc.
"""
import sqlalchemy as sql
import socket
import datetime
import pytz
import geocoder
import enum

import user

def getDatabaseUri(configFile="../libs/config"):
    with open(configFile) as f:
        f.readline() # first line tells format
        line = f.readline()
        details = line.split(',')
        uri = "{}://{}:{}@{}:{}/{}".format(details[0], details[1],
                                        details[2], details[3],
                                        details[4], details[5])
        return uri


#### GLOBALS ####
DATABASEURI = getDatabaseUri()
engine = sql.create_engine(DATABASEURI)
#### GLOBALS ####

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

def check_user_exists(userID):
    """
    @params:
        @userID: str

    @returns:
        @True if user exists
        @False else
    """
    conn = engine.connect()
    query_str = 'SELECT userid FROM Users;'
    cursor = conn.execute(query_str)
    for row in cursor:
        if row['userid'] == userID:
            cursor.close()
            return True
    cursor.close()
    return False

def verify_password(userID, password):
    """
    """
    conn = engine.connect()
    cursor = conn.execute("""SELECT password FROM Users WHERE
                          userID = %s;""", (userID))
    actual = cursor.fetchone()['password']
    cursor.close()
    return actual == password

def update_password(userID, newPass):
    """
    """
    conn = engine.connect()
    cursor = conn.execute("""UPDATE Users SET password = %s
                          WHERE userID = %s;""", (newPass, userID))
    cursor.close()

def insert_user(client):
    """
    @params:
        @client is of type user
    """
    conn = engine.connect()
    cursor = conn.execute("""INSERT INTO Users (userID, password,
                          realName, whoami)
                          VALUES (%s, %s, %s, %s);""",
                          (client.nick, client.password,
                           client.real_name, client.whoami))
    cursor.close()

def get_bio(userID):
    conn = engine.connect()
    cursor = conn.execute("""SELECT bio FROM Users WHERE
                          userID = %s;""", (userID))
    bio = cursor.fetchone()['bio']
    cursor.close()
    return bio

def update_bio(userID, bio):
    conn = engine.connect()
    cursor = conn.execute("""UPDATE Users SET bio = %s
                          WHERE userID = %s;""", (bio, userID))
    cursor.close()

def insert_login(sock, userID):
    """
    @params:
        @sock: socket connected to IRC server
        @user: client's user object
    """
    now = datetime.datetime.utcnow()
    ip, port = sock.getsockname()
    # this gives an internal ip... so need to make a phony connection
    # to get actual ip
    ip = get_local_ip()
    lat, lon = geocoder.ip("me").latlng
    conn = engine.connect()
    cursor = conn.execute("""INSERT INTO UserMetadata (loginIp, loginPort, loginTime, loginLat,
                          loginLong, userID)
                          VALUES (%s, %s, %s, %s, %s, %s);""", (ip, port,
                                                               now,
                                                               lat, lon,
                                                               userID))
    cursor.close()

def check_server_exists(serverID):
    conn = engine.connect()
    cursor = conn.execute("""SELECT serverName from Servers;""")
    for row in cursor:
        if row[0] == serverID:
            cursor.close()
            return True
    cursor.close()
    return False


def insert_server(serverID):
    """
    @params:
        @sock: socket server using to listen
        @serverID: server name, randomly generated
    """
    # @TODO: idea: instead of randomly generating worthless serverID,
    # require cLI args for a server name
    conn = engine.connect()

    cursor = conn.execute("""INSERT INTO Servers (servername)
                          VALUES (%s);""", (serverID))
    cursor.close()

def insert_server_metadata(sock, serverID):
    now = datetime.datetime.utcnow()
    ip, port = sock.getsockname()
    # this gives an internal ip... so need to make a phony connection
    # to get actual ip
    ip = get_local_ip()
    lat, lon = geocoder.ip("me").latlng
    conn = engine.connect()
    cursor = conn.execute("""INSERT INTO ServerMetadata (startuptime,
                          privateIP, privatePort, privateLat, privateLong,
                          serverName)
                          VALUES (%s, %s, %s, %s, %s, %s);""", (now,
                                                                ip, port,
                                                                lat, lon,
                                                                serverID))
    cursor.close()

def check_channel_exists(channel_name):
    conn = engine.connect()
    cursor = conn.execute("""SELECT channelName from Channels;""")
    for row in cursor:
        if row['channelName'] == channel_name:
            cursor.close()
            return True
    cursor.close()
    return False

def insert_channel(channel_name, channel_topic, serverName):
    """
    """
    conn = engine.connect()

    cursor = conn.execute("""INSERT INTO Channels (channelName, channelTopic,
                          serverName)
                          VALUES (%s, %s, %s);""", (channel_name,
                                                    channel_topic,
                                                    serverName))
    cursor.close()

def insert_msg(channel_name, client, msg, serverName):
    """
    @params:
        @channel_name: the name of this channel on server serverName
        @client: of type user, the one sending the msg
        @msg: the message being broadcasted across the server
        @serverName: the unique serverName identifying the server
    """
    conn = engine.connect()

    now = datetime.datetime.utcnow()

    # get rid of extra info preceding msg
    # PRIVMSG <#channel> :<msg>
    msg = msg[msg.find(":") + 1:]

    cursor = conn.execute("""INSERT INTO ChatLogs (userID, originTime,
                          content, channelName, serverName)
                          VALUES (%s, %s, %s, %s, %s);""", (client.nick,
                                                            now,
                                                            msg,
                                                            channel_name,
                                                            serverName))
    cursor.close()

def insert_connection(channelID, client, status_enum, serverName):
    """
    @TODO: copy params and stuff from below function.
        come up with cleaner way of calling this function.
        maybe separate nick from being both username and displayname.
    """
    conn = engine.connect()

    cursor = conn.execute("""INSERT INTO connections (userName,
                          serverName, connStatus, displayName)
                          VALUES (%s, %s, %s, %s);""", (client.nick,
                                                        serverName,
                                                        str(status_enum),
                                                        client.nick))
    cursor.close()

def get_serverRoles(userID, serverName):
    """
    @returns: None, None if serverRoles does not exist
    """
    conn = engine.connect()
    cursor = conn.execute("""SELECT (permissions, displayName) FROM ServerRoles
                          WHERE userID = %s AND serverName = %s;""",
                          (userID, serverName))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        return None, None
    status, displayName = result[0].split(',')
    status, displayName = status[1:], displayName[:len(displayName) - 1]
    cursor.close()
    return Status[status], displayName

def insert_serverRoles(userID, serverName, status_enum, displayName=None):
    if not displayName:
        displayName = userID
    conn = engine.connect()
    cursor = conn.execute("""INSERT INTO ServerRoles (userID,
                          serverName, permissions, displayName)
                          VALUES (%s, %s, %s, %s);""", (userID, serverName,
                                                        str(status_enum),
                                                        displayName))
    cursor.close()

def get_channelRoles(userID, channelName, serverName):
    """
    @returns: None if channelRoles does not exist
    """
    conn = engine.connect()
    cursor = conn.execute("""SELECT (permissions) FROM ChannelRoles
                          WHERE userID = %s AND channelName = %s
                          AND serverName = %s;""", (userID,
                                                    channelName,
                                                    serverName))
    result = cursor.fetchone()
    if not result:
        return None
    status = result[0]
    cursor.close()
    return Status[status]

def insert_channelRoles(userID, channelName, serverName, status_enum):
    conn = engine.connect()
    cursor = conn.execute("""INSERT INTO ChannelRoles (userID, channelName,
                          serverName, permissions) VALUES
                          (%s, %s, %s, %s);""", (userID, channelName,
                                                 serverName, str(status_enum)))
    cursor.close()

class FriendResultCode(enum.Enum):
    FriendDontExist = 1
    AlreadyFriends = 2
    InsertSuccessful = 3

def insert_friend(client, theirFriendsUserID):
    """
    @params:
        @client: of type user, the user currently using the client
        @theirFriendsID: the user.nick of the friend they're adding

    @returns:
        False, if friendship already exists
        True, if friendship was created
    """
    conn = engine.connect()

    cursor = conn.execute("""SELECT DISTINCT userid from Users;""")
    friend_exists = False
    for row in cursor:
        if row[0] == theirFriendsUserID:
            friend_exists = True
            break

    if not friend_exists:
        cursor.close()
        return FriendResultCode.FriendDontExist


    cursor = conn.execute("""SELECT friend1ID, friend2ID from Friends;""")
    for f1id, f2id in cursor:
        if f1id == client.nick and f2id == theirFriendsUserID:
            cursor.close()
            return FriendResultCode.AlreadyFriends
        if f1id == theirFriendsUserID and f2id == client.nick:
            cursor.close()
            return FriendResultCode.AlreadyFriends

    now = datetime.datetime.utcnow()
    cursor = conn.execute("""INSERT INTO Friends (friend1id, friend2id,
                         established)
                          VALUES (%s, %s, %s);""", (client.nick,
                                                    theirFriendsUserID,
                                                    now))
    cursor.close()
    return FriendResultCode.InsertSuccessful

def fetch_friends(client):
    """
    @params:
        @client: of type user, the user currently using the client

    @returns:
        list of this client's friends
    """
    # @TODO: everything lol
    conn = engine.connect()

    cursor = conn.execute("""SELECT DISTINCT friend2id from Friends
                          WHERE friend1id=%s;""", (client.nick))
    friends = []
    for row in cursor:
        friends.append(row[0])

    cursor.close()
    return friends
