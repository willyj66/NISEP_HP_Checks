#!python
# -*- coding: utf-8 -*-

import logging

# Configure logging level here
LOG_LEVEL = logging.INFO

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

from binascii import b2a_hex, unhexlify, b2a_base64, hexlify
from requests.auth import HTTPBasicAuth
from base64 import standard_b64encode, b64decode, urlsafe_b64encode, urlsafe_b64decode
from hashlib import sha1, sha256

# Python 3.4+
from hashlib import pbkdf2_hmac

import re
import os

def marker_split(s, m1, m2=None):
    start = s.find(m1) + len(m1)
    end = len(s)
    if m2 != None:
        end = s.find(m2)
    return s[start:end]

def get_nonce():
    return b2a_hex(os.urandom(32)).decode()


def get_nonce_16():
    return urlsafe_b64encode(os.urandom(16)).decode()

def get_nonce_24():
    return urlsafe_b64encode(os.urandom(16)).decode()

def _hash_sha256(client_key, algorithm):
    hashFunc = algorithm()
    hashFunc.update(client_key)
    return hashFunc.hexdigest()


def salted_password(salt, iterations, algorithm_name, password):
    dk = pbkdf2_hmac(
        algorithm_name, password.encode(), urlsafe_b64decode(salt), int(iterations)
    )
    encrypt_password = hexlify(dk)
    return encrypt_password


def salted_password_2(salt, iterations, algorithm_name, password):
    logging.debug("password: %s", password)
    logging.debug("salt: %s", salt)
    logging.debug("unhexlify(salt): %s", unhexlify(salt))
    logging.debug(" password.encode(): %s",  password.encode())
    logging.debug(int(iterations))
    dk = pbkdf2_hmac(
        algorithm_name, password.encode(), unhexlify(salt), int(iterations)
    )
    logging.debug("dk: %s", dk)
    encrypt_password = hexlify(dk)
    logging.debug("encrypt_password: %s", encrypt_password)
    return encrypt_password


def base64_no_padding(s):
    encoded_str = urlsafe_b64encode(s.encode())
    encoded_str = encoded_str.decode().replace("=", "")
    return encoded_str


def regex_after_equal(s):
    tmp_str = re.search("\=(.*)$", s, flags=0)
    return tmp_str.group(1)


def _xor(s1, s2):
    tmp = hex(int(s1, 16) ^ int(s2, 16))[2:]
    if (len(tmp) % 2) != 0:
        return '0' + tmp
    return tmp

def _xor2(s1, s2):
    return "{:02x}".format(int(s1, 16) ^ int(s2, 16))
 

if __name__ == "__main__":

    # logging.debug(unhexlify('11b407ef4f01534a138a8599545dc3c943535dac95477d7f1334fec85408197c'))
    # logging.debug(unhexlify('199de3b1e4da5664d045d9f07d75d22eb853e875c788147f1db811bebe8c4282'))
    # result = _xor('11b407ef4f01534a138a8599545dc3c943535dac95477d7f1334fec85408197c', '199de3b1e4da5664d045d9f07d75d22eb853e875c788147f1db811bebe8c4282')
    # logging.debug(result)

    # logging.debug(unhexlify(result))

    logging.debug(unhexlify('2c8728d28f7ca4d17d0fa6041887963a0968046ab5c318ee2f923319029af3c2'))
    logging.debug(unhexlify('39aa3a9b46f3903b699cb775cfed778ecb1080869ba3772a1a98f27a2429c1de'))
    result = _xor('2c8728d28f7ca4d17d0fa6041887963a0968046ab5c318ee2f923319029af3c2', '39aa3a9b46f3903b699cb775cfed778ecb1080869ba3772a1a98f27a2429c1de')

    logging.debug(result)


   