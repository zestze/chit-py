#!/usr/bin/env python3
"""
Module for holding globals
"""

import threading

def init():
    global channel_newusers
    global channel_newusersLock
    global killself_event

    channel_newusers = {}
    channel_newusersLock = threading.Lock()
    killself_event = threading.Event()
