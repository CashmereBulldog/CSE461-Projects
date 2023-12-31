#!/usr/bin/env python
"""
client.py: A Python script for a network communication client.

This script contains functions and logic for a network communication client that connects to a
server on the address passed into the first argument and performs a series of stages involving UDP and
TCP communication. The stages include sending UDP packets, receiving acknowledgments, and extracting
various pieces of information from server responses.

Authors: mchris02@uw.edu, danieb36@uw.edu, rhamilt@uw.edu
Date: 10-25-23
"""
from asyncio import Timeout
import socket
import sys
from time import sleep
sys.path.append("..")
import select
#from src import generate_header, pad_packet, BIND_PORT
from utils import generate_header, pad_packet, BIND_PORT

ATTU_SERVER_ADDR = "attu2.cs.washington.edu"
STUDENT_ID = 857
MAXIMUM_TIMEOUT = 5
MAXIMUM_TIMEOUT_STAGE_B = 0.5  # Maximum time client will wait for an ack from server before sending new one


def stage_a(address):
    """ Stage A for Part 1.
    Sends a single UDP packet containing the string "hello world" without the quotation marks to
    'address' on port 12235
    
    :param address: The address that the client is connecting to
    
    :return: A tuple containing the following integers -
        - num: An integer representing a numerical value from the server's response.
        - length: An integer representing a length value from the server's response.
        - udp_port: An integer representing a port value from the server's response.
        - secret_a: An integer representing a secret key from the server's response.

    Note: If the connection to the server fails or there are issues receiving acks or the secret
    response, the function will return None for the respective values.
    """
    print("***** STAGE A *****")
    txt = b'hello world\0'
    num, length, udp_port, secret_a = None, None, None, None

    # Generate header
    packet = generate_header(len(txt), 0, 1, STUDENT_ID) + txt

    # Create new socket
    try:
        sock_a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e: 
        print ("Error creating socket: %s" % e) 
        sys.exit(1)
    
    # Send the packet to the server
    try:
        sock_a.sendto(packet, (address, BIND_PORT))
    except socket.error:
        print("Error occured while sending packet")
        sock_a.close()
        return None, None, None, None

    # Wait for a response back
    ready = select.select([sock_a], [], [], MAXIMUM_TIMEOUT)
    response_received = False
    while not response_received:
        if ready[0]:
            response_received = True
            result = sock_a.recv(28)
            num = int.from_bytes(result[12:16], byteorder='big')
            length = int.from_bytes(result[16:20], byteorder='big')
            udp_port = int.from_bytes(result[20:24], byteorder='big')
            secret_a = int.from_bytes(result[24:28], byteorder='big')
            print(f"num:      {num}\n"
                  f"length:   {length}\n"
                  f"udp_port: {udp_port}\n"
                  f"secret_a: {secret_a}")

    # Close socket
    print("***** STAGE A *****\n")
    sock_a.close()
    return num, length, udp_port, secret_a

def stage_b(address, num, length, udp_port, secret_a):
    """ Stage B for Part 1
    Sends num UDP packets to the server on port udp_port. Each data packet is size length+4. Each
    payload contains all zeros.

    :param address: The address that the client is connecting to
    :param num: An integer representing the number of UDP packets to send to the server.
    :param length: An integer representing the length of the payload in each packet.
    :param udp_port: An integer representing the port to which the socket connects.
    :param secret_a: An integer representing a secret key to be included in the packet headers.

    :return: A tuple containing the following integers -
        - tcp_port: An integer representing a TCP port value from the server's response.
        - secret_b: An integer representing a secret key from the server's response.

    Note: If the connection to the server fails or there are issues receiving acks or the secret
    response, the function will return None for the respective values.
    """
    print("***** STAGE B *****")

    # Create new socket
    try:
        sock_b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e: 
        print ("Error creating socket: %s" % e) 
        sys.exit(1)

    # Send num packets
    for i in range(num):
        print ("Sending packet", i)
        packet = generate_header(length + 4, secret_a, 1, STUDENT_ID) \
            + i.to_bytes(4, byteorder='big') \
            + (b'\0' * length)

        # Pad payload of size(len + 4) so that it is divisible by 4
        packet = pad_packet(packet)

        ack_received = False

        while not ack_received:
            try:
                bytes_sent = 0
                while bytes_sent == 0:
                    bytes_sent = sock_b.sendto(packet, (address, udp_port))
                # Listen for ack response
                ready = select.select([sock_b], [], [], MAXIMUM_TIMEOUT_STAGE_B)
                if ready[0]:
                    acked_packet_id = -1
                    try:
                        result = sock_b.recv(16)
                        acked_packet_id = int.from_bytes(result[12:16], byteorder='big')
                    except Exception as e:
                        print("The error on trying to receive data was ", e)

                    if acked_packet_id == i:
                        ack_received = True
                    else:
                        print("Unknown acked_packet_id received")
            except Exception as e:
                print("an error occurred:", e)

    # Listen for secret response
    tcp_port = None
    secret_b = None
    ready = select.select([sock_b], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        result = sock_b.recv(20)
        tcp_port = int.from_bytes(result[12:16], byteorder='big')
        secret_b = int.from_bytes(result[16:20], byteorder='big')
        print(f"tcp_port: {tcp_port}\n"
              f"secret_b: {secret_b}")

    # Close socket
    sock_b.close()

    print("***** STAGE B *****\n")
    return tcp_port, secret_b


def stage_c(address, tcp_port):
    """ Stage C for Part 1
    Server sends three integers: num2, len2, secretC, and a character c

    :param address: The address that the client is connecting to
    :param tcp_port: An integer representing the TCP port to connect to on the server.
    :param secret_a: An integer representing a secret key to be included in the packet headers.

    :return: A tuple containing the following integers -
        - num2: Integer from server's response.
        - len2: Integer from server's response.
        - secret_c: An integer representing a secret key from the server's response.
        - c: char from server's response.
    """
    print("***** STAGE C *****")
    num2, len2, secret_c, c = None, None, None, None

    # Create new TCP socket
    try:
        sock_c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error as e: 
        print ("Error creating socket: %s" % e) 
        sys.exit(1)
    
    # Connect to server
    try: 
        sock_c.connect((address, tcp_port))
    except socket.gaierror as e: 
        print ("Address-related error connecting to server: %s" % e) 
        sys.exit(1) 
    except socket.error as e: 
        print ("Connection error: %s" % e) 
        sys.exit(1)

    ready = select.select([sock_c], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        result = sock_c.recv(28)
        num2 = int.from_bytes(result[12:16], byteorder='big')
        len2 = int.from_bytes(result[16:20], byteorder='big')
        secret_c = int.from_bytes(result[20:24], byteorder='big')
        c = result[24].to_bytes(1, byteorder='big')
        print(f"num2:     {num2}\n"
              f"len2:     {len2}\n"
              f"secret_c: {secret_c}\n"
              f"c:        {c}")
    else:
        print("Did not receive TCP response")

    print("***** STAGE C *****\n")
    return num2, len2, secret_c, c, sock_c


def stage_d(tcp_port, num2, len2, secret_c, c, connection):
    """ Stage D for Part 1
    Sends num2 TCP packets to the server on port udp_port. Each data packet is size len2 + 4. Each
    payload contains all bytes of the character c.

    :param tcp_port: An integer representing the port to which the socket connects.
    :param num2: An integer representing the number of TCP packets to send to the server.
    :param len2: An integer representing the length of the payload in each packet.
    :param secret_c: An integer representing a secret key to be included in the packet headers.
    :param c: A character with which to fill the payload

    :return:
        - secret_d: An integer representing a secret key from the server's response.

    Note: If the connection to the server fails or there are issues receiving acks or the secret
    response, the function will return None for the respective values.
    """
    print("***** STAGE D *****")

    # Pass in socket from stage c
    sock_d = connection

    # Send num packets
    for i in range(num2):
        packet = generate_header(len2, secret_c, 1, STUDENT_ID) + (c * len2)
        if len(packet) % 4 != 0:
            packet += (c * (4 - len(packet) % 4))
        print("Sending packet", i)
        packet = pad_packet(packet)

        # Send message to server
        sock_d.send(packet)

    # Listen for secret response
    secret_d = None
    try:
        ready = select.select([sock_d], [], [], MAXIMUM_TIMEOUT)
        if ready[0]:
            result = sock_d.recv(16)
            secret_d = int.from_bytes(result[12:16], byteorder='big')
        else:
            print("Did not receive TCP response")
    except Exception as e:
        print("an error occurred:", e)
        sock_d.close()

    # Close socket
    sock_d.close()
    
    print(f"secret_d: {secret_d}")
    print("***** STAGE D *****\n")
    return secret_d


def main():
    """ Main function that calls the stages for the client """
    if len(sys.argv) == 1:
        # Default to connecting to attu2.cs.washington.edu
        address = ATTU_SERVER_ADDR
    elif len(sys.argv) == 2:
        address = sys.argv[1]
    else:
        print("Usage: python client.py [server_address=attu2.cs.washington.edu]")
        return
    num, length, udp_port, secret_a = stage_a(address)
    tcp_port, secret_b = stage_b(address, num, length, udp_port, secret_a)
    num2, len2, secret_c, c, sock_c = stage_c(address, tcp_port)
    secret_d = stage_d(tcp_port, num2, len2, secret_c, c, sock_c)
    print(f"Final list of secrets:\n"
          f"   Secret A: {secret_a}\n"
          f"   Secret B: {secret_b}\n"
          f"   Secret C: {secret_c}\n"
          f"   Secret D: {secret_d}")

if __name__ == "__main__":
    main()
