import io
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime

from PIL import Image, ImageTk

from client import ChatClient

# File extensions treated as video
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"}


# ====================================================================== #
#  Connection dialog — shown before the main chat window                 #
# ====================================================================== #

class ConnectDialog:
    """
    Small popup that asks the user for server host and port.
    Supports local mode (127.0.0.1) and hosted Railway mode.
    """

    def __init__(self):
        self.host   = None
        self.port   = None
        self.result = False   # True if user clicked Connect

        self.window = tk.Tk()
        self.window.title("Connect to Server")
        self.window.geometry("360x280")
        self.window.configure(bg="#075e54")
        self.window.resizable(False, False)
        self.window.eval("tk::PlaceWindow . center")

        self._build()

    def _build(self):
        tk.Label(
            self.window, text="💬 Python Chat",
            font=("Arial", 18, "bold"),
            fg="white", bg="#075e54"
        ).pack(pady=(24, 4))

        tk.Label(
            self.window, text="Connect to server",
            font=("Arial", 10), fg="#b2dfdb", bg="#075e54"
        ).pack()

        form = tk.Frame(self.window, bg="#075e54")
        form.pack(pady=18, padx=30, fill="x")

        # Host
        tk.Label(form, text="Host:", fg="white", bg="#075e54",
                 font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self.host_entry = tk.Entry(form, font=("Arial", 11), width=26)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1, padx=(10, 0))

        # Port
        tk.Label(form, text="Port:", fg="white", bg="#075e54",
                 font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=4)
        self.port_entry = tk.Entry(form, font=("Arial", 11), width=26)
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=1, column=1, padx=(10, 0))

        tk.Button(
            self.window,
            text="Connect",
            bg="#25d366", fg="white",
            font=("Arial", 12, "bold"),
            relief="flat", cursor="hand2",
            command=self._on_connect
        ).pack(pady=(4, 0), ipadx=20, ipady=6)

        self.window.bind("<Return>", lambda e: self._on_connect())

    def _on_connect(self):
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not host:
            messagebox.showwarning("Input Error", "Please enter a host.", parent=self.window)
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("Input Error", "Port must be a number.", parent=self.window)
            return

        self.host   = host
        self.port   = port
        self.result = True
        self.window.destroy()

    def show(self):
        self.window.mainloop()
        return self.result


# ====================================================================== #
#  Main chat window                                                       #
# ====================================================================== #

class ChatUI:
    def __init__(self, host="127.0.0.1", port=5000):
        self.window = tk.Tk()
        self.window.title("Python Chat")
        self.window.geometry("520x740")
        self.window.configure(bg="#ece5dd")
        self.window.resizable(False, False)

        self.hd_mode     = tk.BooleanVar(value=False)
        self._photo_refs = []   # Prevent Tkinter GC from deleting images

        self.client = ChatClient(
            host=host,
            port=port,
            on_message    = self.receive_message,
            on_image      = self.receive_image,
            on_file       = self.receive_file,
            on_video      = self.receive_video,
            on_connect    = self._on_connect,
            on_disconnect = self._on_disconnect,
        )
        self.client.connect()

        self._build_ui()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  Build UI                                                            #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self._build_header()
        self._build_chat_area()
        self._build_toolbar()
        self._build_input_row()

    def _build_header(self):
        header = tk.Frame(self.window, bg="#075e54", height=58)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="💬  Python Chat",
            fg="white", bg="#075e54",
            font=("Arial", 15, "bold")
        ).pack(side="left", padx=14, pady=10)

        # HD Image toggle in the header (like WhatsApp quality switch)
        tk.Checkbutton(
            header, text="HD Image",
            variable=self.hd_mode,
            fg="white", bg="#075e54",
            selectcolor="#128c7e",
            activeforeground="white",
            activebackground="#075e54",
            font=("Arial", 10)
        ).pack(side="right", padx=12)

    def _build_chat_area(self):
        self.chat_area = scrolledtext.ScrolledText(
            self.window,
            wrap=tk.WORD,
            font=("Arial", 11),
            bg="#ece5dd",
            state="disabled",
            relief="flat",
            padx=6, pady=6
        )
        self.chat_area.pack(fill="both", expand=True)

        # ---- Tag styles ---- #

        # Sent (right-aligned green bubble)
        self.chat_area.tag_config(
            "me",
            justify="right",
            foreground="#1a1a1a",
            background="#dcf8c6",
            lmargin1=80, lmargin2=80,
            rmargin=8,
            spacing1=2, spacing3=2,
        )

        # Received (left-aligned white bubble)
        self.chat_area.tag_config(
            "friend",
            justify="left",
            foreground="#1a1a1a",
            background="#ffffff",
            lmargin1=8, lmargin2=8,
            rmargin=80,
            spacing1=2, spacing3=2,
        )

        # Timestamp under each bubble
        self.chat_area.tag_config(
            "ts_me",
            justify="right",
            foreground="#999999",
            font=("Arial", 8),
            rmargin=10,
            spacing3=7,
        )
        self.chat_area.tag_config(
            "ts_friend",
            justify="left",
            foreground="#999999",
            font=("Arial", 8),
            lmargin1=10,
            spacing3=7,
        )

        # Centre grey line (system / status messages)
        self.chat_area.tag_config(
            "system",
            justify="center",
            foreground="#888888",
            font=("Arial", 9, "italic"),
            spacing1=4, spacing3=4,
        )

    def _build_toolbar(self):
        bar = tk.Frame(self.window, bg="#f0f0f0", pady=5)
        bar.pack(fill="x", padx=10)

        btn = dict(
            font=("Arial", 10),
            relief="groove",
            cursor="hand2",
            bg="#ffffff",
            fg="#075e54",
            padx=8, pady=2,
        )

        tk.Button(bar, text="🖼  Image",
                  command=self.send_image, **btn).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="🎥  Video",
                  command=self.send_video, **btn).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="📎  File",
                  command=self.send_file,  **btn).pack(side="left")

    def _build_input_row(self):
        row = tk.Frame(self.window, bg="#f0f0f0")
        row.pack(fill="x", padx=10, pady=(4, 10))

        self.entry = tk.Entry(row, font=("Arial", 12), relief="solid", bd=1)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self.entry.bind("<Return>", self.send_message)
        self.entry.focus()

        tk.Button(
            row, text="Send",
            bg="#25d366", fg="white",
            font=("Arial", 11, "bold"),
            relief="flat", cursor="hand2",
            width=8, command=self.send_message
        ).pack(side="right", ipady=5)

    # ------------------------------------------------------------------ #
    #  Bubble helpers                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _now():
        return datetime.now().strftime("%H:%M")

    def _text_bubble(self, sender, text):
        tag, ts, label = self._tags(sender)
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f" {label}: {text} \n", tag)
        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _image_bubble(self, sender, img_bytes, filename):
        tag, ts, label = self._tags(sender)
        self.chat_area.config(state="normal")
        try:
            img = Image.open(io.BytesIO(img_bytes))
            img.thumbnail((260, 260))
            photo = ImageTk.PhotoImage(img)
            self._photo_refs.append(photo)
            self.chat_area.insert(tk.END, f" {label} 📷 {filename}\n", tag)
            self.chat_area.image_create(tk.END, image=photo)
            self.chat_area.insert(tk.END, "\n")
        except Exception:
            self.chat_area.insert(tk.END, f" {label}: [Image – {filename}] \n", tag)
        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _video_bubble(self, sender, filename, saved_path=None):
        tag, ts, label = self._tags(sender)
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f" {label} 🎥 {filename}\n", tag)

        if saved_path:
            btn = tk.Button(
                self.chat_area,
                text="  ▶  Play Video  ",
                bg="#075e54", fg="white",
                font=("Arial", 10, "bold"),
                relief="flat", cursor="hand2",
                command=lambda p=saved_path: self._open_video(p),
            )
            self.chat_area.window_create(tk.END, window=btn)
            self.chat_area.insert(tk.END, "\n")

        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _file_bubble(self, sender, filename, saved=False):
        tag, ts, label = self._tags(sender)
        note = "  ✔ saved to received/" if saved else ""
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f" {label}: 📎 {filename}{note} \n", tag)
        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _system_msg(self, text):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f"{text}\n", "system")
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    @staticmethod
    def _tags(sender):
        """Return (bubble_tag, timestamp_tag, label) for a given sender."""
        if sender == "me":
            return "me", "ts_me", "You"
        return "friend", "ts_friend", "Friend"

    # ------------------------------------------------------------------ #
    #  Open video in system default media player                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _open_video(path):
        try:
            abs_path = os.path.abspath(path)
            if sys.platform == "win32":
                os.startfile(abs_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", abs_path])
            else:
                subprocess.Popen(["xdg-open", abs_path])
        except Exception as e:
            print(f"[UI] Could not open video: {e}")

    # ------------------------------------------------------------------ #
    #  Send actions                                                        #
    # ------------------------------------------------------------------ #

    def send_message(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self._text_bubble("me", text)
        self.client.send_text(text)
        self.entry.delete(0, tk.END)

    def send_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff")]
        )
        if not path:
            return
        hd = self.hd_mode.get()
        self._system_msg(f"Sending image ({'HD' if hd else 'Compressed'})…")
        with open(path, "rb") as f:
            self._image_bubble("me", f.read(), os.path.basename(path))
        self.client.send_image(path, hd=hd)

    def send_video(self):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
                ("All files", "*.*"),
            ]
        )
        if not path:
            return
        filename = os.path.basename(path)
        size_mb  = os.path.getsize(path) / (1024 * 1024)
        self._system_msg(f"Sending video: {filename}  ({size_mb:.1f} MB)…")
        self._video_bubble("me", filename)
        self.client.send_video(path)

    def send_file(self):
        path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("All files", "*.*")]
        )
        if not path:
            return
        filename = os.path.basename(path)
        ext      = os.path.splitext(filename)[1].lower()

        # Safety net: if user picks a video through the File dialog, treat it correctly
        if ext in VIDEO_EXTENSIONS:
            size_mb = os.path.getsize(path) / (1024 * 1024)
            self._system_msg(f"Sending video: {filename}  ({size_mb:.1f} MB)…")
            self._video_bubble("me", filename)
            self.client.send_video(path)
        else:
            self._system_msg(f"Sending file: {filename}…")
            self._file_bubble("me", filename)
            self.client.send_file(path)

    # ------------------------------------------------------------------ #
    #  Receive callbacks — always called from background thread           #
    #  → use window.after() to safely update the Tkinter UI              #
    # ------------------------------------------------------------------ #

    def receive_message(self, text):
        self.window.after(0, lambda: self._text_bubble("friend", text))

    def receive_image(self, filename, data):
        os.makedirs("received", exist_ok=True)
        with open(os.path.join("received", filename), "wb") as f:
            f.write(data)
        self.window.after(0, lambda: self._image_bubble("friend", data, filename))

    def receive_video(self, filename, data):
        os.makedirs("received", exist_ok=True)
        save_path = os.path.join("received", filename)
        with open(save_path, "wb") as f:
            f.write(data)
        self.window.after(
            0,
            lambda sp=save_path, fn=filename: self._video_bubble("friend", fn, saved_path=sp)
        )

    def receive_file(self, filename, data):
        os.makedirs("received", exist_ok=True)
        save_path = os.path.join("received", filename)
        with open(save_path, "wb") as f:
            f.write(data)
        ext = os.path.splitext(filename)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            # Safety net: video that arrived via FILE packet still gets Play button
            self.window.after(
                0,
                lambda sp=save_path, fn=filename: self._video_bubble("friend", fn, saved_path=sp)
            )
        else:
            self.window.after(0, lambda: self._file_bubble("friend", filename, saved=True))

    # ------------------------------------------------------------------ #
    #  Connection state callbacks                                          #
    # ------------------------------------------------------------------ #

    def _on_connect(self):
        self.window.after(0, lambda: self._system_msg("✅ Connected to server"))

    def _on_disconnect(self):
        self.window.after(0, lambda: self._system_msg("❌ Disconnected from server"))

    def _on_close(self):
        self.client.disconnect()
        self.window.destroy()

    # ------------------------------------------------------------------ #

    def run(self):
        self.window.mainloop()


# ====================================================================== #
#  Entry point                                                            #
# ====================================================================== #

if __name__ == "__main__":
    dialog = ConnectDialog()
    if dialog.show():
        app = ChatUI(host=dialog.host, port=dialog.port)
        app.run()
