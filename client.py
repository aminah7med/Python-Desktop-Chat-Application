import os
import socket
import threading

from protocol import PacketBuilder, PacketParser


# Default online endpoint — Railway TCP Proxy
ONLINE_HOST = "viaduct.proxy.rlwy.net"
ONLINE_PORT = 39169


class ChatClient:
    """
    TCP chat client.

    Modes:
      Local   : host="127.0.0.1",      port=5000
      Online  : host=ONLINE_HOST,      port=ONLINE_PORT  (Railway TCP Proxy)

    Callbacks (all optional):
      on_message(text)
      on_image(filename, data)
      on_file(filename, data)
      on_video(filename, data)
      on_connect()
      on_disconnect()
    """

    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

    CONNECT_TIMEOUT = 15   # seconds

    def __init__(
        self,
        host=ONLINE_HOST,
        port=ONLINE_PORT,
        on_message=None,
        on_image=None,
        on_file=None,
        on_video=None,
        on_connect=None,
        on_disconnect=None,
    ):
        self.host = host
        self.port = port

        self.on_message    = on_message
        self.on_image      = on_image
        self.on_file       = on_file
        self.on_video      = on_video
        self.on_connect    = on_connect
        self.on_disconnect = on_disconnect

        self.client_socket  = None
        self.running        = False
        self.buffer         = b""

        self._disconnected  = False   # guard: fire on_disconnect only once
        self._lock          = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Connection                                                          #
    # ------------------------------------------------------------------ #

    def connect(self):
        """
        Open TCP connection and start receive thread.
        Returns True on success, False on failure.
        """
        self._disconnected = False
        self.buffer        = b""

        # Reject http/https addresses early with a readable message
        if self.host.startswith("http://") or self.host.startswith("https://"):
            print(
                "[Client] ERROR: host looks like an HTTP URL.\n"
                "         Use the Railway TCP Proxy host, not the HTTPS domain."
            )
            return False

        try:
            print(f"[Client] Connecting to {self.host}:{self.port} ...")

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.client_socket.settimeout(self.CONNECT_TIMEOUT)
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)

            self.running = True
            print(f"[Client] Connected to {self.host}:{self.port}")

            if self.on_connect:
                self.on_connect()

            threading.Thread(target=self._receive_loop, daemon=True).start()
            return True

        except ConnectionRefusedError:
            print(
                f"[Client] Connection refused ({self.host}:{self.port}).\n"
                "         Local: is server.py running?\n"
                "         Online: check Railway TCP Proxy host & port."
            )
        except socket.gaierror as e:
            print(
                f"[Client] DNS error for '{self.host}': {e}\n"
                "         Make sure you are using the TCP Proxy host, not the HTTPS domain."
            )
        except socket.timeout:
            print(
                f"[Client] Timed out after {self.CONNECT_TIMEOUT}s.\n"
                "         Check host/port. Railway proxy can be slow on first connect."
            )
        except OSError as e:
            print(f"[Client] OS error: {e}")
        except Exception as e:
            print(f"[Client] Connection failed: {e}")

        return False

    def disconnect(self):
        """Close connection. Safe to call multiple times."""
        with self._lock:
            if self._disconnected:
                return
            self._disconnected = True

        self.running = False

        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception:
            pass
        finally:
            self.client_socket = None

        print("[Client] Disconnected.")

        if self.on_disconnect:
            self.on_disconnect()

    # ------------------------------------------------------------------ #
    #  Send methods                                                        #
    # ------------------------------------------------------------------ #

    def send_text(self, message):
        self._send(PacketBuilder.build_text(message))

    def send_image(self, file_path, hd=False):
        try:
            from compressor import ImageCompressor

            out_path = (
                ImageCompressor.save_hd_copy(file_path)
                if hd
                else ImageCompressor.compress(file_path)
            )
            if out_path is None:
                print("[Client] Image processing failed.")
                return

            data = ImageCompressor.get_bytes(out_path)
            if data is None:
                print("[Client] Could not read processed image.")
                return

            filename = os.path.basename(file_path)
            self._send(PacketBuilder.build_image(filename, data))

        except Exception as e:
            print(f"[Client] Send image failed: {e}")

    def send_video(self, file_path):
        threading.Thread(target=self._send_binary, args=(file_path,), daemon=True).start()

    def send_file(self, file_path):
        threading.Thread(target=self._send_binary, args=(file_path,), daemon=True).start()

    def _send_binary(self, file_path):
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                data = f.read()
            self._send(PacketBuilder.build_file(filename, data))
            print(f"[Client] Sent {filename}  ({len(data):,} bytes)")
        except Exception as e:
            print(f"[Client] Send binary failed: {e}")

    def _send(self, packet):
        if not self.running or self.client_socket is None:
            print("[Client] Cannot send — not connected.")
            return
        try:
            self.client_socket.sendall(packet)
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.disconnect()

    # ------------------------------------------------------------------ #
    #  Receive loop                                                        #
    # ------------------------------------------------------------------ #

    def _receive_loop(self):
        while self.running:
            try:
                chunk = self.client_socket.recv(65536)

                if not chunk:
                    print("[Client] Server closed connection.")
                    break

                self.buffer += chunk
                self._drain_buffer()

            except ConnectionResetError:
                print("[Client] Connection reset by server.")
                break
            except OSError:
                break   # Socket closed from our side — normal on disconnect()
            except Exception as e:
                if self.running:
                    print(f"[Client] Receive error: {e}")
                break

        self.disconnect()

    def _drain_buffer(self):
        while True:
            packet, self.buffer = PacketParser.extract_one(self.buffer)
            if packet is None:
                break
            self._dispatch(packet)

    def _dispatch(self, packet):
        ptype    = packet["type"]
        filename = packet.get("filename") or ""
        ext      = os.path.splitext(filename)[1].lower()

        if ptype == "text" and self.on_message:
            self.on_message(packet["data"])
        elif ptype == "image" and self.on_image:
            self.on_image(filename, packet["data"])
        elif ptype == "file":
            if ext in self.VIDEO_EXTENSIONS and self.on_video:
                self.on_video(filename, packet["data"])
            elif self.on_file:
                self.on_file(filename, packet["data"])