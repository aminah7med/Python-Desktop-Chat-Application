import base64


class PacketBuilder:

    @staticmethod
    def build_text(message):
        return f"<TEXT>{message}</TEXT>".encode()

    @staticmethod
    def build_image(filename, data):
        # base64-encode binary so closing tag never appears inside payload
        encoded = base64.b64encode(data).decode()
        return f"<IMAGE>{filename}|{encoded}</IMAGE>".encode()

    @staticmethod
    def build_file(filename, data):
        encoded = base64.b64encode(data).decode()
        return f"<FILE>{filename}|{encoded}</FILE>".encode()


class PacketParser:

    # (packet_type, opening_tag, closing_tag)
    TAGS = [
        ("text",  b"<TEXT>",  b"</TEXT>"),
        ("image", b"<IMAGE>", b"</IMAGE>"),
        ("file",  b"<FILE>",  b"</FILE>"),
    ]

    @staticmethod
    def extract_one(buffer):
        """
        Scan the buffer for the first complete packet.
        Returns (packet_dict, remaining_buffer).
        Returns (None, buffer) when no complete packet is found yet.
        This is called repeatedly until None is returned.
        """
        for ptype, open_tag, close_tag in PacketParser.TAGS:
            if not buffer.startswith(open_tag):
                continue

            end = buffer.find(close_tag)
            if end == -1:
                # Packet has started but not finished yet — wait for more data
                return None, buffer

            content = buffer[len(open_tag):end]
            rest    = buffer[end + len(close_tag):]

            if ptype == "text":
                return {
                    "type":     "text",
                    "filename": None,
                    "data":     content.decode(errors="ignore")
                }, rest

            # IMAGE or FILE: split on first "|"
            sep      = content.find(b"|")
            filename = content[:sep].decode()
            raw_data = base64.b64decode(content[sep + 1:])

            return {
                "type":     ptype,
                "filename": filename,
                "data":     raw_data
            }, rest

        # Buffer doesn't start with any known tag — discard until it does
        # (handles stray bytes or partial corruption)
        return None, buffer

    @staticmethod
    def parse(data):
        """Convenience wrapper — parse a single self-contained packet."""
        packet, _ = PacketParser.extract_one(data)
        return packet