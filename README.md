<div align="center">

# 💬 Python Chat Application

**Real-time desktop chat — TCP Sockets · Tkinter GUI · Images, Videos & File Sharing**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-FF6F00?style=for-the-badge)
![Socket](https://img.shields.io/badge/Networking-TCP%20Sockets-00897B?style=for-the-badge)
![Pillow](https://img.shields.io/badge/Media-Pillow-8BC34A?style=for-the-badge)
![Railway](https://img.shields.io/badge/Deploy-Railway-6E50F5?style=for-the-badge&logo=railway&logoColor=white)

> **Final Project — Network-Based Multimedia Applications Course · 2025**

</div>

---

## 📌 Overview

A fully-featured, real-time desktop chat app built **from scratch** in pure Python.  
Clients connect through a central TCP server and exchange **text, images (compressed or HD), videos, and any file** — all inside a clean, WhatsApp-style Tkinter GUI.

The protocol is hand-crafted. No file-transfer libraries. No file-size headers. Packet boundaries are detected using a custom tag-based framing system with Base64-encoded payloads.

---

## 🏗️ Architecture

```
CLIENT 1                        SERVER                        CLIENT 2
┌──────────────┐   TCP packet  ┌──────────────────┐  TCP packet  ┌──────────────┐
│  Tkinter UI  │──────────────▶│   ChatServer     │─────────────▶│  Tkinter UI  │
│  (ui.py)     │◀──────────────│   (Mediator)     │◀─────────────│  (ui.py)     │
│  client.py   │               │   server.py      │              │  client.py   │
└──────────────┘               └──────────────────┘              └──────────────┘

Flow:
  1. Client builds a packet            → sends to server
  2. Server reassembles it from chunks → broadcasts to every other client
  3. Each client parses + renders it   → chat bubble appears in the UI
```

> Clients **never talk to each other directly** — everything goes through the server (Mediator pattern).

---

## 📁 Project Structure

```
chat_project/
│
├── server.py        # TCP server — bind, accept, buffer, broadcast
├── client.py        # TCP client — connect, send, receive, dispatch via callbacks
├── protocol.py      # PacketBuilder + PacketParser (streaming buffer parser)
├── compressor.py    # Image compression: quality=35 (normal) / quality=95 (HD)
├── ui.py            # Tkinter GUI — chat bubbles, toolbar, inline image preview
├── main.py          # One-click launcher: Server + 2 Client windows
│
├── Procfile         # Railway deployment entry point  →  web: python server.py
├── requirements.txt # pip dependencies (Pillow only)
├── .gitignore       # Ignores received/, temp/, __pycache__, etc.
│
├── received/        # Auto-saved incoming files (git-ignored)
└── temp/            # Temp compressed images before send (git-ignored)
```

---

## 🔌 Custom Protocol

No file size is transmitted. Packets use **XML-style tags** as frame delimiters:

```
Text   →  <TEXT>Hello!</TEXT>
Image  →  <IMAGE>photo.jpg|<base64></IMAGE>
File   →  <FILE>video.mp4|<base64></FILE>
```

Binary payloads are **Base64-encoded** so the closing tag can never appear inside them by accident.  
The streaming parser `PacketParser.extract_one(buffer)` pulls complete packets out of a live TCP byte buffer one at a time — correctly reassembling large files that arrive across many TCP chunks.

---

## ✨ Features

| Feature | Status |
|---|---|
| Multithreaded TCP Server | ✅ |
| Text broadcast to all clients | ✅ |
| Image send with JPEG compression (quality 35) | ✅ |
| HD Image mode (quality 95) toggle | ✅ |
| Video send + ▶ Play button | ✅ |
| Generic file send & auto-save | ✅ |
| WhatsApp-style chat bubbles (left / right) | ✅ |
| Timestamps on every message | ✅ |
| Inline image preview (260×260 thumbnail) | ✅ |
| Connect dialog (local or hosted) | ✅ |
| One-click launcher `main.py` | ✅ |
| Railway cloud deployment ready | ✅ |

---

## 🚀 Run Locally

### 1 — Clone

```bash
git clone https://github.com/aminah7med/python-chat-app.git
cd python-chat-app
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3a — One-click launcher (easiest)

```bash
python main.py
```

Click **🚀 Start Server + 2 Clients** — server and two chat windows open automatically.

### 3b — Manual (separate terminals)

```bash
# Terminal 1
python server.py

# Terminal 2 & 3 (each opens a chat window)
python ui.py
```

Leave the connect dialog at defaults (`127.0.0.1` / `5000`) and hit **Connect**.

---

## 📤 Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit — Python Chat Application"
git remote add origin https://github.com/aminah7med/python-chat-app.git
git branch -M main
git push -u origin main
```

---

## ☁️ Deploy Server on Railway

The server runs in the cloud; desktop clients connect to it from anywhere.

### Step 1 — Sign up

[railway.app](https://railway.app) → sign in with GitHub.

### Step 2 — New project

- **New Project → Deploy from GitHub repo** → select `python-chat-app`
- Railway auto-detects `Procfile` and runs `python server.py`

### Step 3 — Expose a TCP port

- Project **Settings → Networking → Add TCP Proxy**
- Railway gives you a public address like:
  ```
  Host: roundhouse.proxy.rlwy.net
  Port: 12345
  ```

### Step 4 — Connect clients to the cloud

Run `ui.py` on any machine and enter:

```
Host: roundhouse.proxy.rlwy.net
Port: 12345
```

Everyone connecting to that address shares the same chat session.

---

## 🧑‍💻 Team

<table>
  <tr>
    <td align="center"><b>👤 Amin Ahmed</b><br/><sub>Team Member</sub></td>
    <td align="center"><b>👤 Mostafa Mohamed Abdel-shafy</b><br/><sub>Team Member</sub></td>
    <td align="center"><b>👤 Mohamed Ramadan</b><br/><sub>Team Member</sub></td>
  </tr>
</table>

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Networking | `socket` — TCP |
| Concurrency | `threading` |
| GUI | `tkinter` + `scrolledtext` |
| Image processing | `Pillow` |
| Protocol | Custom tag framing + Base64 |
| Cloud deployment | Railway (TCP proxy) |

---

## ⚠️ Constraints Met

Per project specification:

- ❌ File size is **NOT** sent before transfer
- ✅ End-of-packet detected via **custom closing tags**
- ❌ No ready-made file-transfer libraries used
- ✅ Binary payloads safely encoded with **Base64**

---

<div align="center">
Made with ❤️ — Network-Based Multimedia Applications · 2025
</div>