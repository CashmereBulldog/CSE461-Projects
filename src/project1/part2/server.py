#!/usr/bin/env python
"""
server.py: A Python script for a web server.

The server's task is to verify whether the client adheres to the protocol and send a response only to the valid client.
    1. The server will start listening on port 12235.
    2. The server can handle multiple clients at a time.
    3. The server verifies the header of every packet received and close any open sockets to the client and/or fail to respond to the client if:
        - unexpected number of buffers have been received
        - unexpected payload, or length of packet or length of packet payload has been received
        - the server does not receive any packets from the client for 3 seconds
        - the server does not receive the correct secret
    4. The Server responds to the client in four stages. In each stage, the server should randomly generate a secret to be sent to the client.

Authors: mchris02@uw.edu, danieb36@uw.edu, rhamilt@uw.edu
Date: 10-25-23
"""
import socket
import sys
sys.path.append("..")
from random import randint, choice
from string import ascii_letters
import threading

from utils import generate_header, pad_packet, check_header, BIND_PORT

MAXIMUM_TIMEOUT = 3  # Socket will close if no response is received for this many seconds


def stage_a():
    """ Stage A for Part 2.
    Client sends a single UDP packet containing the string "hello world" without the quotation marks
    to this server, server responds with an ack of randomly generated numbers

    :return: A tuple containing the following integers -
        - num: An randint representing a numerical value from the server's response.
        - length: A randint representing a length value from the server's response.
        - udp_port: A randint representing a port value from the server's response.
        - secret_a: A randint representing a secret key from the server's response.
        - student_id: The student id of the client to ensure we're getting the
          same messages
    """
    
    print("Starting up server")
    # Create UDP socket
    try:
        listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bind to address and IP
        listener.bind(("localhost", BIND_PORT))
    except socket.error as e: 
        print ("Error creating socket: %s" % e) 
        sys.exit(1)

    while True:
        print("Waiting for responses")
        # Receive a single message
        message, client_addr = listener.recvfrom(24)
        print(f"Received message from client {client_addr}")

        if check_header(message[:12],
                        expected_length=len(b'hello world\0'),
                        expected_secret=0):
            num, length, udp_port, secret_a = randint(3, 20), randint(
                10, 100), randint(12236, 15000), randint(0, 256)

            student_id = int.from_bytes(message[10:12], byteorder='big')
            print("Stage A, student id:", student_id)

            ack = generate_header(16, 0, 2, student_id) \
                + num.to_bytes(4, byteorder='big') \
                + length.to_bytes(4, byteorder='big') \
                + udp_port.to_bytes(4, byteorder='big') \
                + secret_a.to_bytes(4, byteorder='big')

            listener.sendto(ack, client_addr)
            print ("Received part a request from student id", student_id)
            new_thread = threading.Thread(target=stage_b, args=(num, length, udp_port, secret_a, student_id))
            new_thread.start()
            new_thread.join()
        else:
            print("Client message was not formatted correctly")


def stage_b(num, length, udp_port, secret_a, student_id):
    print("Stage B, student id:", student_id)
    # Create UDP socket
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.settimeout(MAXIMUM_TIMEOUT)
        
        # Bind to address and IP
        server.bind(("localhost", udp_port))
    except socket.error as e: 
        print ("Error creating socket: %s" % e) 
        sys.exit(1)

    secret_b, tcp_port = None, None
    iteration = 0
    while iteration < num:
        padding = 4 - (length % 4)
        data, client_addr = server.recvfrom(12 + (length + 4) + padding)

        if len(data) % 4 != 0:
            print("Length of packet is not divisible by 4 :", len(data))
            break

        header_check = check_header(data[:12], length + 4, secret_a)
        if not header_check:
            print('badly formatted header')
            break

        # Payload: First 4 bytes contains integer identifying the packet.
        # The first packet should have this identifier set to 0,
        # while the last packet should have its counter set to num-1
        first_4_bytes = int.from_bytes(data[12:16], byteorder="big")
        if first_4_bytes != iteration:
            print("Iteration is incorrect")
            break

        # Check that the rest of the packet is filled with zeros:
        for item in data[16:]:
            if item != 0:
                print("ERROR: remainder of packet should be filled with zeros!")
                break

        # Randomly decide if ack should be sent.
        to_send = randint(0, 2)
        if to_send > 0:
            # Include the payload identifier of packet in ack.
            message = generate_header(4, secret_a, 2, student_id) + data[12:16]
            server.sendto(message, client_addr)

            # Only increase iteration if ack was sent.
            iteration += 1

        if iteration == num:
            # All num packets were received. Send tcp port number, and a
            # secretB.
            secret_b = randint(0, 500)
            tcp_port = randint(1024, 65353)
            message = generate_header(4, secret_a, 2, student_id) \
                + tcp_port.to_bytes(4, byteorder='big') \
                + secret_b.to_bytes(4, byteorder='big')
            
            # Create TCP socket
            try:
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.settimeout(MAXIMUM_TIMEOUT)
                
                # Bind to address/port and listen for incoming connections
                listener.bind(("localhost", tcp_port))
                listener.listen(MAXIMUM_TIMEOUT)
                print("Listening on port", tcp_port)
                
                # Send client message with tcp port info
                server.sendto(message, client_addr)
            except socket.error as e: 
                print ("Error creating socket: %s" % e) 
                sys.exit(1)

            stage_c(tcp_port, secret_b, student_id, listener)


def stage_c(tcp_port: int, secret_b: int, student_id: int, listener):
    """ Stage C for Part 2.

    Server sends three integers: num2, len2, secretC, and a character c

    :param tcp_port: An integer representing the TCP port to connect to on the server.
    :param secret_b: An integer representing a secret key to be included in the packet headers.
    """
    print("Stage C, student id:", student_id)

    while True:
        try:
            connection, address = listener.accept()
            print(f"New connection with {address[0]} at TCP port {address[1]}")

            # Send data back to the client
            num2, len2, secret_c, c = randint(3, 20), randint(10, 100), randint(0, 256), choice(ascii_letters)
            response = generate_header(13, secret_b, step=2, student_id=student_id) \
                       + num2.to_bytes(4, byteorder='big') \
                       + len2.to_bytes(4, byteorder='big') \
                       + secret_c.to_bytes(4, byteorder='big') \
                       + ord(c).to_bytes(1, byteorder='big')
            response = pad_packet(response)
            connection.send(response)

            # Call Stage D after successful conversation, not closing socket
            stage_d(num2, len2, secret_c, c, student_id, connection)
            break

        except BaseException:
            print("Closing tcp listener")
            listener.close()
            break


def stage_d(num2, len2, secret_c, c, student_id, connection):
    print("Stage D, student id:", student_id)
    packets_received = 0
    valid = True
    while packets_received < num2:
        padding = 0 if (len2 % 4 == 0 ) else 4 - (len2 % 4)
        msg = connection.recv(12 + len2 + padding)  # Header plus length
        if check_header(msg[:12], len2, secret_c):
            packets_received += 1
            valid &= msg[12:] != c * len2
            if not valid:
                break
        else:
            print("Client message was not formatted correctly")

    if valid:
        secret_d = randint(0, 256)
        ack = generate_header(4, secret_c, step=2, student_id=student_id) \
            + secret_d.to_bytes(4, byteorder='big')
        connection.send(ack)
    else:
        print("Client message was not formatted correctly")

    connection.close()

    print("Done with student_id", student_id)


def main():
    """ Main function that calls the stage a for the server. Threads are split from there"""
    stage_a()


if __name__ == "__main__":
    main()
