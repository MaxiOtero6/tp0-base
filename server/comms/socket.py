import logging
import socket
from typing import Optional


class Socket:
    """
    Wrapper around socket.socket to avoid short reads and writes
    """
    _socket: socket.socket
    address: tuple[str, int]

    def __init__(self, address: tuple[str, int], skt: Optional[socket.socket] = None, listen_backlog: int = 5) -> None:
        self.address = address

        if skt:  # Client socket
            self._socket = skt
            return

        # Server socket
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.bind(self.address)
        self._socket.listen(listen_backlog)

    def accept(self) -> "Socket":
        """
        Accept a new client connection and return a new Socket object
        """
        c, addr = self._socket.accept()

        logging.info(
            f'action: accept_connections | result: success | ip: {addr[0]}'
        )

        return Socket(address=addr, skt=c)

    def close(self) -> None:
        """
        Close the socket
        """
        self._socket.close()

    def send_all(self, data: bytes) -> None:
        """
        Send all data to the socket avoiding short writes
        """
        while data:
            sent: int = self._socket.send(data)
            data = data[sent:]

    def recv_all(self) -> bytes:
        """
        Receive all data from the socket avoiding short reads
        """
        data: bytes = b''
        split_buff: list[bytes] = []

        # if a \n is found in the buffer, len(split_buff) will be 2
        while not data or len(split_buff) <= 1:
            if self._recv_buffer:
                split_buff = self._recv_buffer.split(b'\n', 1)

                data += split_buff[0]
                self._recv_buffer = split_buff[1] if len(
                    split_buff) > 1 else b''
                continue

            chunk = self._socket.recv(1024)
            if not chunk:
                raise BrokenPipeError("Connection closed by peer")
            self._recv_buffer += chunk

        return data
