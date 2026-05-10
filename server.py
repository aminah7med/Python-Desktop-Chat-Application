import os
import socket
import threading


class ChatServer:

    def __init__(self):
        self.host = "0.0.0.0"

        # Railway injects PORT as an environment variable.
        # On Railway the value is always a plain TCP port — Railway's TCP Proxy
        # terminates TLS/HTTP *outside* our process, so we just bind to this port.
        # Locally it falls back to 5000.
        self.port = int(os.environ.get("PORT", 5000))

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allows quick restart without "Address already in use" error
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Keep-alive so Railway's idle-connection killer doesn't drop quiet clients
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        # Thread-safe list of connected client sockets
        self.clients      = []
        self.clients_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Start                                                               #
    # ------------------------------------------------------------------ #

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)

        print("=" * 50)
        print("  Python Chat Server")
        print("=" * 50)
        print(f"  Bind host : {self.host}")
        print(f"  Bind port : {self.port}")
        print(f"  Railway?  : {'YES' if os.environ.get('RAILWAY_ENVIRONMENT') else 'NO (local)'}")
        print("  Status    : Running — waiting for clients...")
        print("=" * 50)

        while True:
            try:
                client_socket, client_address = self.server_socket.accept()

                # Enable keep-alive on each accepted socket too
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                with self.clients_lock:
                    self.clients.append(client_socket)

                count = len(self.clients)
                print(f"[+] Client connected    -> {client_address}  |  total: {count}")

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True,
                )
                thread.start()

            except Exception as e:
                print(f"[!] Accept error: {e}")

    # ------------------------------------------------------------------ #
    #  Handle one client                                                   #
    # ------------------------------------------------------------------ #

    def handle_client(self, client_socket, client_address):
        """
        Each client runs in its own thread.
        We keep a per-client byte buffer so large packets (images / videos)
        that arrive in multiple TCP chunks are reassembled correctly.
        """
        buffer = b""

        while True:
            try:
                chunk = client_socket.recv(65536)

                if not chunk:
                    print(f"[~] Clean disconnect from {client_address}")
                    break

                buffer += chunk

                # Extract every complete packet and broadcast it
                while True:
                    packet, buffer = self._extract_packet(buffer)
                    if packet is None:
                        break
                    print(f"[>] Packet from {client_address}  ({len(packet):,} bytes)")
                    self.broadcast(packet, client_socket)

            except ConnectionResetError:
                print(f"[!] Connection reset by {client_address}")
                break
            except OSError as e:
                # Socket was closed from our side (e.g. during shutdown)
                print(f"[!] OSError with {client_address}: {e}")
                break
            except Exception as e:
                print(f"[!] Error with {client_address}: {e}")
                break

        self._remove_client(client_socket, client_address)

    # ------------------------------------------------------------------ #
    #  Packet boundary detection                                           #
    # ------------------------------------------------------------------ #

    PACKET_PAIRS = [
        (b"<TEXT>",  b"</TEXT>"),
        (b"<IMAGE>", b"</IMAGE>"),
        (b"<FILE>",  b"</FILE>"),
    ]

    def _extract_packet(self, buffer):
        """
        Scan the buffer for the first complete packet.
        Returns (complete_packet_bytes, remaining_buffer)
        or      (None, buffer) when no full packet is ready yet.
        """
        for open_tag, close_tag in self.PACKET_PAIRS:
            if not buffer.startswith(open_tag):
                continue

            end = buffer.find(close_tag)
            if end == -1:
                return None, buffer   # Packet started but not finished yet

            end += len(close_tag)
            return buffer[:end], buffer[end:]

        # Buffer starts with unknown bytes — discard until a known tag appears
        earliest = len(buffer)
        for open_tag, _ in self.PACKET_PAIRS:
            idx = buffer.find(open_tag)
            if 0 < idx < earliest:
                earliest = idx

        if earliest < len(buffer):
            print(f"[!] Discarding {earliest} stray bytes before next packet tag")
            return None, buffer[earliest:]

        return None, buffer

    # ------------------------------------------------------------------ #
    #  Broadcast & cleanup                                                 #
    # ------------------------------------------------------------------ #

    def broadcast(self, data, sender_socket):
        """Send data to every connected client except the sender."""
        with self.clients_lock:
            targets = [c for c in self.clients if c != sender_socket]

        dead = []
        for client in targets:
            try:
                client.sendall(data)
            except Exception as e:
                print(f"[!] Broadcast failed to a client: {e}")
                dead.append(client)

        for client in dead:
            self._remove_client(client, "unknown (broadcast failure)")

    def _remove_client(self, client_socket, client_address):
        with self.clients_lock:
            if client_socket in self.clients:
                self.clients.remove(client_socket)

        try:
            client_socket.close()
        except Exception:
            pass

        print(f"[-] Client disconnected -> {client_address}  |  total: {len(self.clients)}")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    server = ChatServer()
    server.start()