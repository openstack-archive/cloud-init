# Copyright 2015 Canonical Ltd.
# This file is part of cloud-init.  See LICENCE file for license information.
#
# vi: ts=4 expandtab

import ctypes
from ctypes import windll
from ctypes import wintypes

AF_UNSPEC = 0
AF_INET = 2
AF_INET6 = 23

VERSION_2_2 = (2 << 8) + 2


class SOCKADDR(ctypes.Structure):
    _fields_ = [
        ('sa_family', wintypes.USHORT),
        ('sa_data', ctypes.c_char * 14),
    ]


class WSADATA(ctypes.Structure):
    _fields_ = [
        ('opaque_data', wintypes.BYTE * 400),
    ]


WSAGetLastError = windll.Ws2_32.WSAGetLastError
WSAGetLastError.argtypes = []
WSAGetLastError.restype = wintypes.INT

WSAStartup = windll.Ws2_32.WSAStartup
WSAStartup.argtypes = [wintypes.WORD, ctypes.POINTER(WSADATA)]
WSAStartup.restype = wintypes.INT

WSACleanup = windll.Ws2_32.WSACleanup
WSACleanup.argtypes = []
WSACleanup.restype = wintypes.INT

WSAAddressToStringW = windll.Ws2_32.WSAAddressToStringW
WSAAddressToStringW.argtypes = [
    ctypes.POINTER(SOCKADDR), wintypes.DWORD, wintypes.LPVOID,
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
WSAAddressToStringW.restype = wintypes.INT

Ws2_32 = windll.Ws2_32
Ws2_32.inet_ntoa.restype = ctypes.c_char_p


def init_wsa(version=VERSION_2_2):
    wsadata = WSADATA()
    WSAStartup(version, ctypes.byref(wsadata))
