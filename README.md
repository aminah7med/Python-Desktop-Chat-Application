<div align="center">

# 💬 Python Chat Application

**A real-time desktop chat application built with Python — TCP sockets, Tkinter GUI, and media sharing.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00?style=for-the-badge)
![Socket](https://img.shields.io/badge/Networking-TCP%20Sockets-00897B?style=for-the-badge)
![Pillow](https://img.shields.io/badge/Media-Pillow-8BC34A?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-blueviolet?style=for-the-badge)

> Final Project — Network-Based Applications Course

</div>

---

## 📌 Overview

A fully-featured, real-time desktop chat application built from scratch in Python. Two or more clients connect through a central TCP server, and can exchange **text messages**, **images** (with optional HD quality), and **any file type** — all displayed in a clean, WhatsApp-inspired GUI.

The protocol is designed manually (no ready-made file-transfer libraries), and the application uses a custom packet framing system to detect end-of-transfer without sending file size headers.

---

## 🏗️ Architecture

```
CLIENT 1                    SERVER                      CLIENT 2
┌──────────┐    TCP      ┌──────────────┐    TCP      ┌──────────┐
│ Tkinter  │────────────▶│  ChatServer  │────────────▶│ Tkinter  │
│   GUI    │◀────────────│  (Mediator)  │◀────────────│   GUI    │
│ client.py│             │  server.py   │             │ client.py│
└──────────┘             └──────────────┘             └──────────┘
```

- Clients **never connect directly** — all data flows through the server
- Server **broadcasts** every packet to all clients except the sender
- Supports **multiple simultaneous clients**

---

## ✨ Features

### ✅ Required
| Feature | Status |
|---|---|
| TCP Socket Programming (Client + Server) | ✅ Done |
| Send & Receive Text Messages | ✅ Done |
| Send Images with Compression | ✅ Done |
| HD Image Toggle (like WhatsApp) | ✅ Done |
| Send Files / Videos | ✅ Done |
| Tkinter GUI | ✅ Done |
| Chat bubbles (left/right aligned) | ✅ Done |
| Custom Protocol (no file size, no libraries) | ✅ Done |

### 🔥 Advanced
| Feature | Status |
|---|---|
| Online Hosting Support (ngrok / Railway) | ✅ Ready |
| Timestamps on every message | ✅ Done |
| Inline image preview in chat | ✅ Done |
| Auto-save received files to `received/` | ✅ Done |
| Buffered TCP receive (handles large packets) | ✅ Done |

---

## 📁 Project Structure

```
chat_project/
│
├── server.py          # TCP server — accepts clients, broadcasts data
├── client.py          # TCP client — connect, send, receive, callbacks
├── protocol.py        # Custom packet builder & parser (Text / Image / File)
├── compressor.py      # Image compression & HD copy using Pillow
├── ui.py              # Tkinter GUI — chat bubbles, toolbar, image preview
├── requirements.txt   # Python dependencies
│
├── assets/            # Local assets (icons, etc.)
├── received/          # Auto-saved received files land here
└── temp/              # Temp folder for compressed images
```

---

## 🔌 Custom Protocol Design

No file size is sent before transfer. Instead, packets use **custom XML-style tags** as framing delimiters:

```
Text   →  <TEXT>Hello World!</TEXT>
Image  →  <IMAGE>photo.jpg|<base64-encoded-bytes></IMAGE>
File   →  <FILE>report.pdf|<base64-encoded-bytes></FILE>
```

Binary payloads are **Base64-encoded** to prevent the closing tag from accidentally appearing inside binary data. The server and client use a streaming buffer approach — accumulating TCP chunks until a full packet is detected.

```python
# PacketParser.extract_one() — scans buffer for a complete packet
packet, remaining_buffer = PacketParser.extract_one(buffer)
```

---

## 🖥️ How to Run

### 1. Clone the Repository

```bash
git clone https://github.com/aminah7med/python-chat-app.git
cd python-chat-app
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Server

```bash
python server.py
```

### 4. Launch Clients (run in separate terminals or machines)

```bash
python ui.py
```

> To connect from another machine, open `ui.py` and change `host="127.0.0.1"` to the server's IP address.

---

## 📡 Online Hosting with ngrok

To make the server accessible over the internet:

```bash
# Install ngrok from https://ngrok.com
ngrok tcp 5000
```

Copy the forwarding address (e.g., `0.tcp.ngrok.io:12345`) and update the client:

```python
self.client = ChatClient(host="0.tcp.ngrok.io", port=12345, ...)
```

---

## 📸 Key Modules

### `protocol.py` — Packet Builder & Parser
Builds and parses packets for text, image, and file types.
Handles streaming extraction from a live TCP buffer via `extract_one()`.

### `server.py` — Chat Server
Accepts multiple clients. Each client gets its own **receive buffer** and **background thread**.
Uses `SO_REUSEADDR` for clean restarts. Broadcasts every complete packet to all other connected clients.

### `client.py` — Chat Client
Connects to server, runs a **daemon receive thread**, accumulates data into a buffer, and dispatches complete packets via callbacks:
- `on_message(text)` — text received
- `on_image(filename, data)` — image received
- `on_file(filename, data)` — file received

### `compressor.py` — Image Compressor
Uses **Pillow** to compress images to JPEG at quality=35 (compressed mode) or quality=100 (HD mode). Handles RGBA/P → RGB conversion automatically.

### `ui.py` — Tkinter GUI
- WhatsApp-style chat bubbles (green = sent, white = received)
- Timestamps on every message
- Inline image preview (thumbnailed to 260×260)
- File/Image send buttons with file dialog
- HD toggle checkbox in the header

---

## 🧑‍💻 Team Members

<table>
  <tr>
    <td align="center">
      <b>👤 Amin Ahmed</b><br/>
      <sub>Team Member</sub>
    </td>
    <td align="center">
      <b>👤 Mostfa Mohamed Abdel-shafy</b><br/>
      <sub>Team Member</sub>
    </td>
    <td align="center">
      <b>👤 Mohamed Ramdan</b><br/>
      <sub>Team Member</sub>
    </td>
  </tr>
</table>

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Networking | `socket` (TCP) |
| Concurrency | `threading` |
| GUI | `tkinter` + `scrolledtext` |
| Image Processing | `Pillow` (PIL) |
| Protocol | Custom — XML-style framing + Base64 |

---

## ⚠️ Tricky Constraints Met

Per the project specification:

- ❌ File size is **NOT** sent before transfer
- ✅ End-of-packet is detected via **custom closing tags**
- ❌ No ready-made file-transfer libraries used
- ✅ Binary data is safely encoded with **Base64**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">
  Made with ❤️ for the Network-Based Applications Final Project
</div>
