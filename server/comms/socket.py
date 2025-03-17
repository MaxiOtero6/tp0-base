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

        while not data or data[-1] != ord('\n'):
            chunk = self._socket.recv(1024)
            if not chunk:
                raise BrokenPipeError("Connection closed by peer")
            data += chunk

        return data[:-1]  # Remove '\n'
