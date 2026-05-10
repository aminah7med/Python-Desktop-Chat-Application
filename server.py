import os
import socket
import threading


class ChatServer:

    def __init__(self):
        self.host = "0.0.0.0"
        self.port = int(os.environ.get("PORT", 5000))

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        self.clients = []
        self.clients_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Start                                                             #
    # ------------------------------------------------------------------ #

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)

        on_railway = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

        print("=" * 50)
        print("  Python Chat Server")
        print("=" * 50)
        print(f"  Host    : {self.host}")
        print(f"  Port    : {self.port}")
        print(f"  Mode    : {'Railway (cloud)' if on_railway else 'Local'}")
        print("  Status  : Running — waiting for clients...")
        print("=" * 50)

        while True:
            try:
                client_socket, client_address = self.server_socket.accept()

                client_socket.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_KEEPALIVE,
                    1
                )

                with self.clients_lock:
                    self.clients.append(client_socket)

                print(
                    f"[+] Client connected    -> "
                    f"{client_address}  |  total: {len(self.clients)}"
                )

                threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                ).start()

            except Exception as e:
                print(f"[!] Accept error: {e}")

    # ------------------------------------------------------------------ #
    #  Handle Client                                                     #
    # ------------------------------------------------------------------ #

    def handle_client(self, client_socket, client_address):

        buffer = b""

        while True:

            try:
                chunk = client_socket.recv(65536)

                if not chunk:
                    print(f"[~] Clean disconnect: {client_address}")
                    break

                # ------------------------------------------------------
                # Railway HTTP health check handling
                # ------------------------------------------------------

                if (
                    chunk.startswith(b"GET ")
                    or chunk.startswith(b"POST ")
                    or b"HTTP/1.1" in chunk
                    or b"Host:" in chunk
                    or b"User-Agent:" in chunk
                ):

                    print(f"[HTTP Probe] {client_address}")

                    response = (
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: text/plain\r\n"
                        b"Content-Length: 2\r\n"
                        b"Connection: keep-alive\r\n"
                        b"\r\n"
                        b"OK"
                    )

                    try:
                        client_socket.sendall(response)
                    except:
                        pass

                    continue

                # ------------------------------------------------------

                buffer += chunk

                while True:

                    packet, buffer = self._extract_packet(buffer)

                    if packet is None:
                        break

                    print(
                        f"[>] Packet from {client_address} "
                        f"({len(packet):,} bytes)"
                    )

                    self.broadcast(packet, client_socket)

            except ConnectionResetError:
                print(f"[!] Reset by {client_address}")
                break

            except OSError as e:
                print(f"[!] OSError {client_address}: {e}")
                break

            except Exception as e:
                print(f"[!] Error {client_address}: {e}")
                break

        self._remove_client(client_socket, client_address)

    # ------------------------------------------------------------------ #
    #  Packet Detection                                                  #
    # ------------------------------------------------------------------ #

    PACKET_PAIRS = [
        (b"<TEXT>",  b"</TEXT>"),
        (b"<IMAGE>", b"</IMAGE>"),
        (b"<FILE>",  b"</FILE>"),
    ]

    def _extract_packet(self, buffer):

        for open_tag, close_tag in self.PACKET_PAIRS:

            if not buffer.startswith(open_tag):
                continue

            end = buffer.find(close_tag)

            if end == -1:
                return None, buffer

            end += len(close_tag)

            packet = buffer[:end]
            remaining = buffer[end:]

            return packet, remaining

        # --------------------------------------------------------------
        # Discard stray / unknown bytes
        # --------------------------------------------------------------

        earliest = len(buffer)

        for open_tag, _ in self.PACKET_PAIRS:
            idx = buffer.find(open_tag)

            if 0 < idx < earliest:
                earliest = idx

        if earliest < len(buffer):

            print(f"[!] Discarding {earliest} stray bytes")

            return None, buffer[earliest:]

        # If completely unknown garbage exists, clear it
        if buffer:
            print(f"[!] Clearing unknown data: {len(buffer)} bytes")

        return None, b""

    # ------------------------------------------------------------------ #
    #  Broadcast                                                         #
    # ------------------------------------------------------------------ #

    def broadcast(self, data, sender_socket):

        with self.clients_lock:
            targets = [
                client
                for client in self.clients
                if client != sender_socket
            ]

        dead_clients = []

        for client in targets:

            try:
                client.sendall(data)

            except Exception as e:
                print(f"[!] Broadcast failed: {e}")
                dead_clients.append(client)

        for dead in dead_clients:
            self._remove_client(dead, "unknown")

    # ------------------------------------------------------------------ #
    #  Remove Client                                                     #
    # ------------------------------------------------------------------ #

    def _remove_client(self, client_socket, client_address):

        with self.clients_lock:

            if client_socket in self.clients:
                self.clients.remove(client_socket)

        try:
            client_socket.close()
        except:
            pass

        print(
            f"[-] Client disconnected -> "
            f"{client_address}  |  total: {len(self.clients)}"
        )


# ------------------------------------------------------------------ #
#  Entry Point                                                       #
# ------------------------------------------------------------------ #

if __name__ == "__main__":

    server = ChatServer()
    server.start()