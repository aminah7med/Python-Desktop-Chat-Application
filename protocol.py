import base64


class PacketBuilder:
    """Builds packets for text, image, and file transfer."""

    @staticmethod
    def build_text(message):
        """<TEXT>hello</TEXT>"""
        # Sanitise: remove any accidental closing tag inside the message
        safe = str(message).replace("</TEXT>", "")
        return f"<TEXT>{safe}</TEXT>".encode()

    @staticmethod
    def build_image(filename, data):
        """<IMAGE>photo.jpg|<base64></IMAGE>"""
        encoded = base64.b64encode(data).decode()
        safe_name = _safe_filename(filename)
        return f"<IMAGE>{safe_name}|{encoded}</IMAGE>".encode()

    @staticmethod
    def build_file(filename, data):
        """<FILE>video.mp4|<base64></FILE>"""
        encoded = base64.b64encode(data).decode()
        safe_name = _safe_filename(filename)
        return f"<FILE>{safe_name}|{encoded}</FILE>".encode()


def _safe_filename(name):
    """Strip the pipe character from filenames so the separator is unambiguous."""
    return str(name).replace("|", "_")


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
        if not buffer:
            return None, buffer

        for ptype, open_tag, close_tag in PacketParser.TAGS:
            if not buffer.startswith(open_tag):
                continue

            end = buffer.find(close_tag)
            if end == -1:
                # Packet started but not fully received yet — wait for more data.
                # Safety cap: if a single incomplete packet has grown beyond 200 MB
                # something is badly wrong — discard it to avoid unbounded RAM growth.
                if len(buffer) > 200 * 1024 * 1024:
                    print(
                        f"[Protocol] Buffer exceeded 200 MB without closing tag "
                        f"for {ptype} — discarding buffer."
                    )
                    return None, b""
                return None, buffer

            content = buffer[len(open_tag):end]
            rest    = buffer[end + len(close_tag):]

            try:
                if ptype == "text":
                    return {
                        "type":     "text",
                        "filename": None,
                        "data":     content.decode(errors="replace"),
                    }, rest

                # IMAGE or FILE — split on first "|"
                sep = content.find(b"|")
                if sep == -1:
                    print(f"[Protocol] Malformed {ptype} packet — no '|' separator, skipping.")
                    return None, rest

                filename  = content[:sep].decode(errors="replace")
                raw_b64   = content[sep + 1:]

                # Validate base64 characters before decoding
                # (catches corruption that would otherwise raise a hard exception)
                raw_b64 = raw_b64.strip()
                try:
                    file_data = base64.b64decode(raw_b64, validate=False)
                except Exception as b64_err:
                    print(f"[Protocol] Base64 decode failed for {ptype} '{filename}': {b64_err} — skipping.")
                    return None, rest

                return {
                    "type":     ptype,
                    "filename": filename,
                    "data":     file_data,
                }, rest

            except Exception as e:
                print(f"[Protocol] Unexpected parse error ({ptype}): {e} — skipping packet.")
                return None, rest

        # Buffer doesn't start with any known opening tag.
        # Discard bytes up to the earliest known tag to re-sync.
        earliest = len(buffer)
        for _, open_tag, _ in PacketParser.TAGS:
            idx = buffer.find(open_tag)
            if 0 < idx < earliest:
                earliest = idx

        if earliest < len(buffer):
            print(f"[Protocol] Discarding {earliest} unrecognised bytes to re-sync.")
            return None, buffer[earliest:]

        # No known tag anywhere in the buffer — nothing to do yet
        return None, buffer

    @staticmethod
    def parse(data):
        """
        Convenience wrapper — parse a single self-contained packet.
        Used when you already have exactly one complete packet in `data`.
        """
        packet, _ = PacketParser.extract_one(data)
        return packet