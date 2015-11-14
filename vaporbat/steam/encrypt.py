import zlib

from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto import Random

steam_public = '''-----BEGIN PUBLIC KEY-----
MIGdMA0GCSqGSIb3DQEBAQUAA4GLADCBhwKBgQDf7BrWLBBmLBc1OhSwfFkRf53T
2Ct64+AVzRkeRuh7h3SiGEYxqQMUeYKO6UWiSRKpI2hzic9pobFhRr3Bvr/WARvY
gdTckPv+T1JzZsuVcNfFjrocejN1oWI0Rrtgt4Bo+hOneoo3S57G9F1fOpn5nsQ6
6WOiu4gZKODnFMBCiQIBEQ==
-----END PUBLIC KEY-----'''

steam_rsa_key = PKCS1_OAEP.new(RSA.importKey(steam_public))

def make_session_key():
    key = Random.new().read(32)
    crypted_key = steam_rsa_key.encrypt(key)
    crc32 = zlib.crc32(crypted_key)
    return key, crypted_key, crc32

def encrypt(data, key):
    # add pkcs7 padding
    l = 16 - (len(data) % 16)
    data += chr(l) * l

    iv = Random.new().read(AES.block_size)
    cipher = AES.new(key, AES.MODE_ECB)
    crypted_iv = cipher.encrypt(iv)

    cipher = AES.new(key, AES.MODE_CBC, IV=iv)
    return crypted_iv + cipher.encrypt(data)

def decrypt(data, key):
    cipher = AES.new(key, AES.MODE_ECB)
    crypted_iv, data = data[:16], data[16:]
    iv = cipher.decrypt(crypted_iv)

    cipher = AES.new(key, AES.MODE_CBC, IV=iv)
    plain = cipher.decrypt(data)

    # remove pkcs7 padding
    l = ord(plain[-1])
    if 0 < l <= 16:
        plain = plain[:-l]

    return plain
