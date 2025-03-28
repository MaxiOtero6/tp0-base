import signal
import logging
from threading import Thread
from comms.socket import Socket
from common.utils import Bet, has_won, load_bets, store_bets
from comms.packet import BetDeserializationError, PacketHeader, deserialize_bets, deserialize_header
from common.bet_monitor import Action, BetMonitor


class Server:
    def __init__(self, port: int, listen_backlog: int, clients_amount: int):
        # Initialize server socket
        self._server_socket = Socket(
            address=('', port), listen_backlog=listen_backlog
        )

        self.__clients: list[tuple[Socket, Thread]] = []

        self.__bet_monitor: BetMonitor = BetMonitor(clients_amount)
        self._running = False

        signal.signal(signal.SIGTERM, self.__shutdown)

    def run(self) -> None:
        """
        Server accepts multiple new connections and starts a new thread for each one
        """

        self._running = True

        while self._running:
            try:
                client_sock: Socket = self.__accept_new_connection()
                client_thread: Thread = Thread(
                    target=self.__handle_client_connection, args=(client_sock,)
                )

                self.__reap_clients()

                self.__clients.append((client_sock, client_thread))
                client_thread.start()

            except OSError as e:
                if self._running:
                    logging.error(
                        f"action: accept_connections | result: fail | error: {str(e)}")

    def __handle_client_connection(self, client_sock: Socket) -> None:
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            running: bool = True
            while running:
                msg: bytes = client_sock.recv_all()
                addr: tuple[str, int] = client_sock.address

                logging.info(
                    f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}'
                )

                header, body = deserialize_header(msg)

                if header == PacketHeader.BET.value:
                    self.__handle_bet(client_sock, body)
                elif header == PacketHeader.BETDRAW.value:
                    self.__handle_draw(client_sock, body)
                elif header == PacketHeader.DRAWRESULTS.value:
                    self.__handle_bet_results(client_sock, body)
                elif header == PacketHeader.SHUTDOWN_CONNECTION.value:
                    self.__handle_shutdown(client_sock, addr[0])
                    running = False
                else:
                    logging.error(
                        f"action: receive_message | result: fail | error: invalid header"
                    )

        except (ValueError, OSError) as e:
            logging.error(
                f"action: receive_message | result: fail | error: {str(e)}"
            )
        finally:
            client_sock.close()

    def __handle_shutdown(self, client_sock: Socket, ip: str) -> None:
        """
        Send a shutdown ack to the client
        """
        client_sock.send_all(f"{PacketHeader.SHUTDOWN_CONNECTION.value} success\n".encode("utf-8"))
        logging.info(f"action: cerrar_conexion | result: success | ip: {ip}")

    def __handle_bet(self, client_sock: Socket, msg: str) -> None:
        """
        Store the bets received from the client
        If the bets are not correctly deserialized, a fail message is sent
        """
        try:
            bet_batch: list[Bet] = deserialize_bets(msg)

            self.__bet_monitor.push_action(
                (Action.STORE_BETS, bet_batch)
            )

            logging.info(
                f"action: apuesta_recibida | result: success | cantidad: {len(bet_batch)}"
            )

            success_msg: bytes = f"{PacketHeader.BET.value} success\n".encode("utf-8")
            client_sock.send_all(success_msg)
        except BetDeserializationError as e:
            logging.error(
                f"action: apuesta_recibida | result: fail | cantidad: {e.bets_len}"
            )

            fail_msg: bytes = f"{PacketHeader.BET.value} fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)

    def __handle_draw(self, client_sock: Socket, msg: str) -> None:
        """
        Confirm the draw of a specific agency
        If the agency id is not a number, a fail message is sent
        """
        try:
            client_id: int = int(msg)

            self.__bet_monitor.push_action(
                (Action.REGISTER_READY_AGENCY, client_id)
            )

            logging.info(
                f"action: confirmacion_sorteo | result: success | id: {client_id}"
            )

            success_msg: bytes = f"{PacketHeader.BETDRAW.value} success\n".encode("utf-8")
            client_sock.send_all(success_msg)
        except ValueError as e:
            logging.error(
                f"action: confirmacion_sorteo | result: fail"
            )

            fail_msg: bytes = f"{PacketHeader.BETDRAW.value} fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)

    def __handle_bet_results(self, client_sock: Socket, msg: str) -> None:
        """
        Send the results of the bet draw to the client
        If the agency id is not found because it has not drawn yet, a fail message is sent
        If the agency id is not found because it has already been sent, a fail message is sent
        If the agency id is not a number, a fail message is sent
        """
        try:
            agency_id: int = int(msg)

            winners: list[Bet] = self.__bet_monitor.request_winners(agency_id)
            winners_documents: str = "&".join([i.document for i in winners])

            winners_msg: bytes = f"{PacketHeader.DRAWRESULTS.value} success {winners_documents}\n".encode(
                "utf-8")

            logging.info(
                f"action: resultados_apuestas | result: success | id: {agency_id} | cantidad: {len(winners)}"
            )

            client_sock.send_all(winners_msg)
        except (ValueError, KeyError) as e:
            fail_msg: bytes = f"{PacketHeader.DRAWRESULTS.value} fail\n".encode("utf-8")
            client_sock.send_all(fail_msg)

    def __accept_new_connection(self) -> Socket:
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info('action: accept_connections | result: in_progress')
        return self._server_socket.accept()

    def __reap_clients(self) -> None:
        """
        Reap clients

        Function that checks if any of the clients have finished their
        communication and removes them from the list
        """

        def _client_is_alive(client_socket: Socket, client_thread: Thread) -> bool:
            if client_thread.is_alive():
                return True

            client_socket.close()
            client_thread.join()
            return False

        self.__clients = [
            (client_sock, client_thread)
            for client_sock, client_thread in self.__clients
            if _client_is_alive(client_sock, client_thread)
        ]

    def __shutdown_clients(self) -> None:
        """
        Shutdown all clients

        Function that closes all the client sockets and stops all the client threads
        """

        for client_sock, client_thread in self.__clients:
            client_sock.close()
            client_thread.join()

    def __shutdown(self, signum, frame):
        """
        Shutdown server

        Function that closes the server socket, stops the server loop
        and waits for the bet monitor to join
        """
        self._running = False
        self._server_socket.close()
        self.__shutdown_clients()
        self.__bet_monitor.shutdown()

        signal_name: str = signal.Signals(signum).name
        logging.info(
            f'action: exit | result: success | signal: {signal_name}')
