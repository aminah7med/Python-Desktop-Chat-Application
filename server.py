import os
import socket
import threading


class ChatServer:

    def __init__(self):
        # Railway injects PORT as an environment variable.
        # Locally it falls back to 5000.
        self.host = "0.0.0.0"
        self.port = int(os.environ.get("PORT", 5000))

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allows quick restart without "Address already in use" error
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Thread-safe list of connected client sockets
        self.clients      = []
        self.clients_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Start                                                               #
    # ------------------------------------------------------------------ #

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

        print("=" * 40)
        print("  Python Chat Server")
        print("=" * 40)
        print(f"  Host : {self.host}")
        print(f"  Port : {self.port}")
        print("  Status: Running — waiting for clients...")
        print("=" * 40)

        while True:
            try:
                client_socket, client_address = self.server_socket.accept()

                with self.clients_lock:
                    self.clients.append(client_socket)

                print(f"[+] Client connected    -> {client_address}  |  total: {len(self.clients)}")

                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
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
                return None, buffer   # Packet started but not finished

            end += len(close_tag)
            return buffer[:end], buffer[end:]

        # Buffer starts with unknown bytes — discard until a known tag appears
        for open_tag, _ in self.PACKET_PAIRS:
            idx = buffer.find(open_tag)
            if idx > 0:
                print(f"[!] Discarding {idx} stray bytes")
                return None, buffer[idx:]

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
            except Exception:
                dead.append(client)

        # Clean up any clients that failed during broadcast
        for client in dead:
            self._remove_client(client, "unknown")

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
