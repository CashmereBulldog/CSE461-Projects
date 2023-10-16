"""
main.py: A Python script for a network communication client.

This script contains functions and logic for a network communication client that connects to a server
on the address "attu2.cs.washington.edu" and performs a series of stages involving UDP and TCP
communication. The stages include sending UDP packets, receiving acknowledgments, and extracting
various pieces of information from server responses.

The script also defines utility functions for generating header bytes for TCP and UDP payloads.

Authors: mchris02@uw.edu, danieb36@uw.edu, rhamilt@uw.edu
Date: 10-17-23
"""
import socket
import select
import time
from utils import generate_header, BIND_PORT

SERVER_ADDR = "attu2.cs.washington.edu"
STUDENT_ID = 857
MAXIMUM_TIMEOUT = 5
MAXIMUM_TIMEOUT_STAGE_B = 0.5


def stage_a():
    """ Stage A for Part 1.
    Sends a single UDP packet containing the string "hello world" without the quotation marks to
    attu2.cs.washington.edu on port 12235

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send a packet to the given port
    sock.sendto(packet, (SERVER_ADDR, BIND_PORT))

    # Wait for a response back
    ready = select.select([sock], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        print("Recieved response")
        result = sock.recv(28)
        num = int.from_bytes(result[12:16], byteorder='big')
        length = int.from_bytes(result[16:20], byteorder='big')
        udp_port = int.from_bytes(result[20:24], byteorder='big')
        secret_a = int.from_bytes(result[24:28], byteorder='big')
        print(f"num:      {num}\n"
              f"length:   {length}\n"
              f"udp_port: {udp_port}\n"
              f"secret_a: {secret_a}")

    # Close socket
    print("Closing socket")
    print("***** STAGE A *****\n")
    sock.close()
    return (num, length, udp_port, secret_a)


def stage_b(num, length, udp_port, secret_a):
    """ Stage B for Part 1
    Sends num UDP packets to the server on port udp_port. Each data packet is size length+4. Each
    payload contains all zeros.

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
    sockB = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Send num packets
    for i in range(num):
        packet = generate_header(length + 4, secret_a) + i.to_bytes(4, byteorder='big') + (b'\0' * length)

        # Pad payload of size(len + 4) so that it is divisible by 4
        # TODO: write helper function to automatically pad packet --
        # packet_pad()
        if len(packet) % 4 != 0:
            print(f"Packet is invalid size of {len(packet)}")
            packet += (b'\0' * (4 - len(packet) % 4))
            print(f"Packet successfully padded to size {len(packet)}")

        ack_recieved = False
        print("sending packet", i)

        while not ack_recieved:
            try:
                sockB.sendto(packet, (SERVER_ADDR, udp_port))
                # Listen for ack response
                ready = select.select([sockB], [], [], MAXIMUM_TIMEOUT_STAGE_B)
                if ready[0]:
                    result = sockB.recv(16)
                    acked_packet_id = int.from_bytes(
                        result[12:16], byteorder='big')
                    if acked_packet_id == i:
                        ack_recieved = True
                    else:
                        print("Unknown acked_packet_id recieved")
            except Exception as e:
                print("an error occured:", e)

    # Listen for secret response
    tcp_port = None
    secret_b = None
    ready = select.select([sockB], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        result = sockB.recv(20)
        tcp_port = int.from_bytes(result[12:16], byteorder='big')
        secret_b = int.from_bytes(result[16:20], byteorder='big')
        print(f"tcp_port: {tcp_port}\n"
              f"secret_b: {secret_b}")

    # Close socket
    print("Closing socket")
    sockB.close()

    print("***** STAGE B *****\n")
    return tcp_port, secret_b


def stage_c(tcp_port, secret_b):
    """ Stage C for Part 1
    Server sends three integers: num2, len2, secretC, and a character c

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

    # Connect socket
    sockC = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockC.connect((SERVER_ADDR, tcp_port))

    """
    Technically the packet doesn't need to be made, but it doesn't really make
    sense that they would give us a secret_b that we don't need to send
    # Create packet
    packet = generate_header(0, secret_b, 1, STUDENT_ID) # No body, length is 0

    # Send message to server
    sockC.send(packet)
    """

    ready = select.select([sockC], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        result = sockC.recv(28)
        num2 = int.from_bytes(result[12:16], byteorder='big')
        len2 = int.from_bytes(result[16:20], byteorder='big')
        secret_c = int.from_bytes(result[20:24], byteorder='big')
        c = result[24]
        print(f"num2:     {num2}\n"
              f"len2:     {len2}\n"
              f"secret_c: {secret_c}\n"
              f"c:        {c}")
    else:
        print("Did not receive TCP response")

    # Close socket
    print("Closing socket")
    sockC.close()

    print("***** STAGE C *****\n")
    return num2, len2, secret_c, c


def stage_d(tcp_port, num2, len2, secret_c, c):
    """ Stage D for Part 1
    Sends num2 TCP packets to the server on port udp_port. Each data packet is size len2+4. Each
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

    # Create new socket
    sockD = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sockD.connect((SERVER_ADDR, tcp_port))

    # Send num packets
    for i in range(num2):
        packet = generate_header(len2, secret_c, 1, STUDENT_ID) \
                 + (c.to_bytes(1, byteorder="big") * len2)

        print ("Sending packet", i)
        # Send message to server
        sockD.send(packet)
        time.sleep(0.5)


    # Listen for secret response
    secret_d = None
    ready = select.select([sockD], [], [], MAXIMUM_TIMEOUT)
    if ready[0]:
        result = sockD.recv(16)
        secret_d = int.from_bytes(result[12:16], byteorder='big')
        print(f"secret_d: {secret_d}")

    # Close socket
    print("Closing socket")
    sockD.close()

    print ("***** STAGE D *****\n")
    return secret_d


def main():
    """ Main function that calls the stages for the client """
    num, length, udp_port, secret_a = stage_a()
    tcp_port, secret_b = stage_b(num, length, udp_port, secret_a)
    num2, len2, secret_c, c = stage_c(tcp_port, secret_b)
    secret_d = stage_d(tcp_port, num2, len2, secret_c, c)
    print ("Part one finished with final secret_d of", secret_d)


if __name__ == "__main__":
    main()