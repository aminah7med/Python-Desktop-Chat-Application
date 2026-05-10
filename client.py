import os
import socket
import threading

from protocol import PacketBuilder, PacketParser


class ChatClient:

    # Any file with these extensions is routed to on_video() callback
    VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}

    def __init__(self, host="127.0.0.1", port=5000,
                 on_message=None, on_image=None, on_file=None, on_video=None):
        self.host = host
        self.port = port

        # Callbacks set by the UI layer
        self.on_message = on_message   # on_message(text: str)
        self.on_image   = on_image     # on_image(filename: str, data: bytes)
        self.on_file    = on_file      # on_file(filename: str, data: bytes)
        self.on_video   = on_video     # on_video(filename: str, data: bytes)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = False
        self.buffer  = b""

    def connect(self):
        try:
            self.client_socket.connect((self.host, self.port))
            self.running = True

            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()
            print("Connected to server")

        except Exception as e:
            print("Connection failed:", e)

    # ------------------------------------------------------------------ #
    #  Send methods                                                        #
    # ------------------------------------------------------------------ #

    def send_text(self, message):
        try:
            self.client_socket.sendall(PacketBuilder.build_text(message))
        except Exception as e:
            print("Send text failed:", e)

    def send_image(self, file_path, hd=False):
        try:
            from compressor import ImageCompressor
            out = ImageCompressor.save_hd_copy(file_path) if hd else ImageCompressor.compress(file_path)
            data   = ImageCompressor.get_bytes(out)
            packet = PacketBuilder.build_image(os.path.basename(file_path), data)
            self.client_socket.sendall(packet)
        except Exception as e:
            print("Send image failed:", e)

    def send_video(self, file_path):
        """Send a video file — runs in background thread so UI stays responsive."""
        def _worker():
            try:
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    data = f.read()
                self.client_socket.sendall(PacketBuilder.build_file(filename, data))
                print(f"Video sent: {filename} ({len(data):,} bytes)")
            except Exception as e:
                print("Send video failed:", e)

        threading.Thread(target=_worker, daemon=True).start()

    def send_file(self, file_path):
        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                data = f.read()
            self.client_socket.sendall(PacketBuilder.build_file(filename, data))
        except Exception as e:
            print("Send file failed:", e)

    # ------------------------------------------------------------------ #
    #  Receive loop                                                        #
    # ------------------------------------------------------------------ #

    def _receive_loop(self):
        while self.running:
            try:
                chunk = self.client_socket.recv(65536)
                if not chunk:
                    break
                self.buffer += chunk
                self._process_buffer()
            except Exception:
                break
        self.disconnect()

    def _process_buffer(self):
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
            # ✅ Route to video even if sent via generic File button
            if ext in self.VIDEO_EXTENSIONS and self.on_video:
                self.on_video(filename, packet["data"])
            elif self.on_file:
                self.on_file(filename, packet["data"])

    # ------------------------------------------------------------------ #

    def disconnect(self):
        self.running = False
        try:
            self.client_socket.close()
        except Exception:
            pass