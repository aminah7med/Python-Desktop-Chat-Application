import base64


class PacketBuilder:
    """Builds packets for text, image, and file transfer."""

    @staticmethod
    def build_text(message):
        """<TEXT>hello</TEXT>"""
        return f"<TEXT>{message}</TEXT>".encode()

    @staticmethod
    def build_image(filename, data):
        """
        <IMAGE>photo.jpg|<base64></IMAGE>
        Binary data is base64-encoded so the closing tag never
        appears inside the payload by accident.
        """
        encoded = base64.b64encode(data).decode()
        return f"<IMAGE>{filename}|{encoded}</IMAGE>".encode()

    @staticmethod
    def build_file(filename, data):
        """<FILE>video.mp4|<base64></FILE>"""
        encoded = base64.b64encode(data).decode()
        return f"<FILE>{filename}|{encoded}</FILE>".encode()


class PacketParser:
    """Parses packets from a live TCP byte buffer."""

    # (type_name, opening_tag, closing_tag)
    TAGS = [
        ("text",  b"<TEXT>",  b"</TEXT>"),
        ("image", b"<IMAGE>", b"</IMAGE>"),
        ("file",  b"<FILE>",  b"</FILE>"),
    ]

    @staticmethod
    def extract_one(buffer):
        """
        Scan the buffer for the FIRST complete packet.

        Returns:
            (packet_dict, remaining_buffer)  — when a full packet is found
            (None,        buffer)            — when no full packet yet

        packet_dict keys:
            type     : "text" | "image" | "file"
            filename : str | None
            data     : str (for text) | bytes (for image/file)
        """
        for ptype, open_tag, close_tag in PacketParser.TAGS:
            if not buffer.startswith(open_tag):
                continue

            end = buffer.find(close_tag)
            if end == -1:
                # Packet has started but hasn't finished arriving yet
                return None, buffer

            content       = buffer[len(open_tag):end]
            rest          = buffer[end + len(close_tag):]

            try:
                if ptype == "text":
                    return {
                        "type":     "text",
                        "filename": None,
                        "data":     content.decode(errors="ignore")
                    }, rest

                # IMAGE or FILE — split on first "|"
                sep_index = content.find(b"|")
                if sep_index == -1:
                    # Malformed packet — skip it
                    print(f"[Protocol] Malformed {ptype} packet — no separator, skipping.")
                    return None, rest

                filename  = content[:sep_index].decode(errors="ignore")
                raw_b64   = content[sep_index + 1:]
                file_data = base64.b64decode(raw_b64)

                return {
                    "type":     ptype,
                    "filename": filename,
                    "data":     file_data
                }, rest

            except Exception as e:
                print(f"[Protocol] Parse error ({ptype}): {e} — skipping packet.")
                return None, rest

        # Buffer doesn't start with any known tag.
        # Discard bytes until the next known opening tag.
        earliest = len(buffer)
        for _, open_tag, _ in PacketParser.TAGS:
            idx = buffer.find(open_tag)
            if 0 < idx < earliest:
                earliest = idx

        if earliest < len(buffer):
            print(f"[Protocol] Discarding {earliest} unrecognised bytes.")
            return None, buffer[earliest:]

        return None, buffer

    @staticmethod
    def parse(data):
        """
        Convenience wrapper — parse a single self-contained packet.
        Used when you already have exactly one packet in `data`.
        """
        packet, _ = PacketParser.extract_one(data)
        return packet
