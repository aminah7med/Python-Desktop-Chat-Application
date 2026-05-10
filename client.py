import os
import socket
import threading

from protocol import PacketBuilder, PacketParser


class ChatClient:
    """
    TCP chat client.

    Supports two modes:
      - Local  : host="127.0.0.1", port=5000  (default)
      - Hosted : host="your-app.railway.app",  port=<Railway port>

    Callbacks (all optional, set by the UI layer):
      on_message(text: str)
      on_image(filename: str, data: bytes)
      on_file(filename: str, data: bytes)
      on_video(filename: str, data: bytes)
      on_connect()
      on_disconnect()
    """

    # File extensions that are routed to on_video() instead of on_file()
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

    def __init__(
        self,
        host="127.0.0.1",
        port=5000,
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

        self.client_socket = None
        self.running       = False
        self.buffer        = b""

    # ------------------------------------------------------------------ #
    #  Connection                                                          #
    # ------------------------------------------------------------------ #

    def connect(self):
        """Connect to server and start the receive thread."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)           # Connection timeout
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)         # Back to blocking mode
            self.running = True

            print(f"[Client] Connected to {self.host}:{self.port}")

            if self.on_connect:
                self.on_connect()

            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()

        except ConnectionRefusedError:
            print(f"[Client] Connection refused — is the server running on {self.host}:{self.port}?")
        except socket.timeout:
            print(f"[Client] Connection timed out — check host/port.")
        except Exception as e:
            print(f"[Client] Connection failed: {e}")

    def disconnect(self):
        """Cleanly close the connection."""
        self.running = False
        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception:
            pass

        if self.on_disconnect:
            self.on_disconnect()

        print("[Client] Disconnected.")

    # ------------------------------------------------------------------ #
    #  Send methods                                                        #
    # ------------------------------------------------------------------ #

    def send_text(self, message):
        self._send(PacketBuilder.build_text(message))

    def send_image(self, file_path, hd=False):
        """Compress (or HD) an image then send it."""
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
        """Send a video file — runs in a background thread to keep UI responsive."""
        threading.Thread(
            target=self._send_binary,
            args=(file_path,),
            daemon=True
        ).start()

    def send_file(self, file_path):
        """Send any generic file."""
        threading.Thread(
            target=self._send_binary,
            args=(file_path,),
            daemon=True
        ).start()

    def _send_binary(self, file_path):
        """Read a file from disk and send it as a FILE packet (used by both video and file)."""
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                data = f.read()
            packet = PacketBuilder.build_file(filename, data)
            self._send(packet)
            print(f"[Client] Sent: {filename}  ({len(data):,} bytes)")
        except Exception as e:
            print(f"[Client] Send binary failed: {e}")

    def _send(self, packet):
        """Low-level send — catches broken pipe and similar errors."""
        try:
            self.client_socket.sendall(packet)
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.disconnect()

    # ------------------------------------------------------------------ #
    #  Receive loop (background thread)                                    #
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
            except Exception as e:
                if self.running:
                    print(f"[Client] Receive error: {e}")
                break

        self.disconnect()

    def _drain_buffer(self):
        """Extract and dispatch every complete packet in the buffer."""
        while True:
            packet, self.buffer = PacketParser.extract_one(self.buffer)
            if packet is None:
                break
            self._dispatch(packet)

    def _dispatch(self, packet):
        """Route a parsed packet to the correct callback."""
        ptype    = packet["type"]
        filename = packet.get("filename") or ""
        ext      = os.path.splitext(filename)[1].lower()

        if ptype == "text" and self.on_message:
            self.on_message(packet["data"])

        elif ptype == "image" and self.on_image:
            self.on_image(filename, packet["data"])

        elif ptype == "file":
            # Route video files to on_video, everything else to on_file
            if ext in self.VIDEO_EXTENSIONS and self.on_video:
                self.on_video(filename, packet["data"])
            elif self.on_file:
                self.on_file(filename, packet["data"])
