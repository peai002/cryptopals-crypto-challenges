from random import randint
import socket
from sys import argv
from Crypto.Cipher import AES
from hashlib import sha1
from os import urandom
import argparse
from ch09 import pkcs

# suggested usage: in two unix terminals enter the following commands (one
# command per terminal, order matters):
# python ch33.py -B -p 12345
# python ch33.py -A -p 12345
#
# What should happen: Bob and Alice establish a shared key. Alice can now write
# to Bob, encrypting their communication on the wire!

def modexp(a, b, m):
   s = 1
   while b != 0:
      if b & 1:
         s = (s * a)%m
      b >>= 1
      a = (a * a)%m;
   return s

# modexp(A, b, p) == modexp(B, a, p)

class DHKeyAgreement:
    def __init__(self):
        self.p = int('ffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024'
                'e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd'
                '3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec'
                '6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f'
                '24117c4b1fe649286651ece45b3dc2007cb8a163bf0598da48361'
                'c55d39a69163fa8fd24cf5f83655d23dca3ad961c62f356208552'
                'bb9ed529077096966d670c354e4abc9804f1746c08ca237327fff'
                'fffffffffffff', 16
                )
        self.g = 2

    def hello(self):
        a = randint(0, self.p - 1)
        A = modexp(self.g, a, self.p)
        return self.p, self.g, A, a

    def response(self, p, g):
        b = randint(0, p - 1)
        B = modexp(g, b, p)
        return b, B

    def acknowledgement(self, key, message):
        '''s is the shared secret'''
        iv = urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(message)
        return ciphertext, iv

    def keyagree(self, key, ctext, iv):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        message = cipher.decrypt(ctext)

        iv = urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(message)

        return ciphertext, iv

    def check(self, key, ctext, iv, message):
        cipher = AES.new(key, AES.MODE_CBC, iv)
        testmessage = cipher.decrypt(ctext)
        if testmessage == message:
            print('Connection up and running!')
        else:
            print('Could not validate connection')


def Bob(port):
    #open port, establish socket.

    host = 'localhost'
    s = socket.socket()
    s.bind((host, port))
    s.listen(1)
    print('Port open')
    conn, addr = s.accept()
    print('Connected by', addr)

    data = conn.recv(1024)
    p, g, A = data.decode().split()
    p = int(p); g = int(g); A = int(A)
    print('received parameters')

    obj = DHKeyAgreement()
    b, B = obj.response(p, g)
    conn.sendall(str(B).encode())
    print('sent key exchange information')

    shared_secret = str(modexp(A, b, p)).encode()
    sha = sha1()
    sha.update(shared_secret)
    shared_key = sha.digest()
    shared_key = shared_key[:16]
    print('secret key generated')


    data = conn.recv(1024)
    print('received confirmation request')
    ciphertext, iv = data[:-16], data[-16:]
    ciphertext2, iv2 = obj.keyagree(shared_key, ciphertext, iv)
    conn.sendall(ciphertext2+iv2)
    print('sending response. connection up and running')
    # print("secret key, shared secret: ", shared_key, shared_secret)

    def conversation_listen():
        cipher = AES.new(shared_key, AES.MODE_CBC, b'a'*16)
        while True:
            data = conn.recv(1024)
            text = cipher.decrypt(data)
            print(pkcs.unpad(text, 16).decode())

    conversation_listen()

    conn.close()

def Alice(port):
    host = 'localhost'
    s = socket.socket()
    s.connect((host, port))
    print('connected to host')

    obj = DHKeyAgreement()
    p, g, A, a = obj.hello()
    data = b'%i %i %i' % (p, g, A)
    s.sendall(data)
    print('sent parameters')

    data = s.recv(1024)
    B = int(data.decode())
    print('received key information')
    shared_secret = str(modexp(B, a, p)).encode()
    sha = sha1()
    sha.update(shared_secret)
    shared_key = sha.digest()
    shared_key = shared_key[:16]
    print('secret key generated')

    message = urandom(32)
    ciphertext, iv = obj.acknowledgement(shared_key, message)
    s.sendall(ciphertext + iv)
    print('sending confirmation request')

    data = s.recv(1024)
    obj.check(shared_key, data[:-16], data[-16:], message)

    def conversation_speak():
        print('you can now write to Bob')
        cipher = AES.new(shared_key, AES.MODE_CBC, b'a'*16)
        while True:
            text = input().encode()
            ctext = cipher.encrypt(pkcs.pad(text, 16))
            s.sendall(ctext)

    conversation_speak()

    s.close()

    # print("secret key, shared secret: ", shared_key, shared_secret)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-A", "--Alice", action="store_true")
    group.add_argument("-B", "--Bob", action="store_true")
    group.add_argument("-M", "--Mallory", action="store_true")
    parser.add_argument("-p", "--port", nargs=1, default=[12344],
                        type=int)

    args = parser.parse_args()

    if len(args.port) == 1:
        portA = portB = args.port[0]
    if args.Alice:
        Alice(portA)
    if args.Bob:
        Bob(portB)
