import io
import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, scrolledtext
from datetime import datetime

from PIL import Image, ImageTk

from client import ChatClient


class ChatUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Chat Application")
        self.window.geometry("520x740")
        self.window.configure(bg="#ece5dd")
        self.window.resizable(False, False)

        # HD toggle state
        self.hd_mode = tk.BooleanVar(value=False)

        # Keep PhotoImage refs alive (tkinter GC bug)
        self._photo_refs = []

        # Connect client with all four callbacks
        self.client = ChatClient(
            on_message=self.receive_message,
            on_image=self.receive_image,
            on_file=self.receive_file,
            on_video=self.receive_video,
        )
        self.client.connect()

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self._build_header()
        self._build_chat_area()
        self._build_toolbar()
        self._build_input_row()

    def _build_header(self):
        header = tk.Frame(self.window, bg="#075e54", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="💬  Python Chat",
            fg="white", bg="#075e54",
            font=("Arial", 15, "bold")
        ).pack(side="left", padx=15, pady=12)

        tk.Checkbutton(
            header,
            text="HD Image",
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
            padx=6,
            pady=6
        )
        self.chat_area.pack(fill="both", expand=True)

        # My messages — green bubble, right-aligned
        self.chat_area.tag_config(
            "me",
            justify="right",
            foreground="#1a1a1a",
            background="#dcf8c6",
            lmargin1=90, lmargin2=90,
            rmargin=10,
            spacing1=2, spacing3=2,
        )

        # Friend messages — white bubble, left-aligned
        self.chat_area.tag_config(
            "friend",
            justify="left",
            foreground="#1a1a1a",
            background="#ffffff",
            lmargin1=10, lmargin2=10,
            rmargin=90,
            spacing1=2, spacing3=2,
        )

        # Timestamps
        self.chat_area.tag_config(
            "ts_me",
            justify="right",
            foreground="#888888",
            font=("Arial", 8),
            rmargin=12,
            spacing3=6,
        )
        self.chat_area.tag_config(
            "ts_friend",
            justify="left",
            foreground="#888888",
            font=("Arial", 8),
            lmargin1=12,
            spacing3=6,
        )

        # System / info messages
        self.chat_area.tag_config(
            "system",
            justify="center",
            foreground="#888888",
            font=("Arial", 9, "italic"),
            spacing1=3, spacing3=3,
        )

    def _build_toolbar(self):
        """Row of action buttons above the text input."""
        toolbar = tk.Frame(self.window, bg="#f0f0f0", pady=4)
        toolbar.pack(fill="x", padx=10)

        btn_style = dict(
            bg="#ffffff", fg="#075e54",
            font=("Arial", 10),
            relief="groove",
            cursor="hand2",
            padx=6
        )

        tk.Button(toolbar, text="🖼  Image",
                  command=self.send_image, **btn_style).pack(side="left", padx=(0, 6))

        tk.Button(toolbar, text="🎥  Video",
                  command=self.send_video, **btn_style).pack(side="left", padx=(0, 6))

        tk.Button(toolbar, text="📎  File",
                  command=self.send_file, **btn_style).pack(side="left")

    def _build_input_row(self):
        row = tk.Frame(self.window, bg="#f0f0f0")
        row.pack(fill="x", padx=10, pady=(4, 10))

        self.entry = tk.Entry(row, font=("Arial", 12), relief="solid", bd=1)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self.entry.bind("<Return>", self.send_message)

        tk.Button(
            row,
            text="Send",
            bg="#25d366", fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            cursor="hand2",
            width=8,
            command=self.send_message
        ).pack(side="right", ipady=5)

    # ------------------------------------------------------------------ #
    #  Chat area helpers                                                   #
    # ------------------------------------------------------------------ #

    def _now(self):
        return datetime.now().strftime("%H:%M")

    def _add_text_bubble(self, sender, text):
        tag    = "me"    if sender == "me" else "friend"
        ts_tag = "ts_me" if sender == "me" else "ts_friend"
        label  = "You"   if sender == "me" else "Friend"

        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f" {label}: {text} \n", tag)
        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts_tag)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _add_image_bubble(self, sender, img_bytes, filename):
        tag    = "me"    if sender == "me" else "friend"
        ts_tag = "ts_me" if sender == "me" else "ts_friend"
        label  = "You"   if sender == "me" else "Friend"

        self.chat_area.config(state="normal")

        try:
            image = Image.open(io.BytesIO(img_bytes))
            image.thumbnail((260, 260))
            photo = ImageTk.PhotoImage(image)
            self._photo_refs.append(photo)

            self.chat_area.insert(tk.END, f" {label} 📷 {filename}\n", tag)
            self.chat_area.image_create(tk.END, image=photo)
            self.chat_area.insert(tk.END, "\n")

        except Exception:
            self.chat_area.insert(tk.END, f" {label}: [Image: {filename}] \n", tag)

        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts_tag)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _add_video_bubble(self, sender, filename, saved_path=None):
        """
        Insert a video bubble with a clickable ▶ Play button.
        When clicked, the video opens in the system's default media player.
        """
        tag    = "me"    if sender == "me" else "friend"
        ts_tag = "ts_me" if sender == "me" else "ts_friend"
        label  = "You"   if sender == "me" else "Friend"

        self.chat_area.config(state="normal")

        # Header line
        self.chat_area.insert(tk.END, f" {label} 🎥 {filename}\n", tag)

        # ▶ Play button — only shown for received videos (saved_path is set)
        if saved_path:
            btn = tk.Button(
                self.chat_area,
                text="  ▶  Play Video  ",
                bg="#075e54",
                fg="white",
                font=("Arial", 10, "bold"),
                relief="flat",
                cursor="hand2",
                command=lambda p=saved_path: self._open_video(p)
            )
            self.chat_area.window_create(tk.END, window=btn)
            self.chat_area.insert(tk.END, "\n")

        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts_tag)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _add_file_bubble(self, sender, filename, saved=False):
        tag    = "me"    if sender == "me" else "friend"
        ts_tag = "ts_me" if sender == "me" else "ts_friend"
        label  = "You"   if sender == "me" else "Friend"
        note   = "  ✔ saved to received/" if saved else ""

        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f" {label}: 📎 {filename}{note} \n", tag)
        self.chat_area.insert(tk.END, f"  {self._now()}\n", ts_tag)
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    def _add_system(self, text):
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, f"{text}\n", "system")
        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    # ------------------------------------------------------------------ #
    #  Open video in system default player (cross-platform)              #
    # ------------------------------------------------------------------ #

    def _open_video(self, path):
        try:
            abs_path = os.path.abspath(path)
            if sys.platform == "win32":
                os.startfile(abs_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", abs_path])
            else:
                subprocess.Popen(["xdg-open", abs_path])
        except Exception as e:
            print("Could not open video:", e)

    # ------------------------------------------------------------------ #
    #  Send actions (called from UI thread)                               #
    # ------------------------------------------------------------------ #

    def send_message(self, event=None):
        text = self.entry.get().strip()
        if not text:
            return
        self._add_text_bubble("me", text)
        self.client.send_text(text)
        self.entry.delete(0, tk.END)

    def send_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp *.tiff")]
        )
        if not file_path:
            return

        hd   = self.hd_mode.get()
        mode = "HD" if hd else "Compressed"
        self._add_system(f"Sending image ({mode})…")

        with open(file_path, "rb") as f:
            local_data = f.read()
        self._add_image_bubble("me", local_data, os.path.basename(file_path))

        self.client.send_image(file_path, hd=hd)

    def send_video(self):
        file_path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
                ("All files", "*.*"),
            ]
        )
        if not file_path:
            return

        filename = os.path.basename(file_path)
        size_mb  = os.path.getsize(file_path) / (1024 * 1024)

        self._add_system(f"Sending video: {filename} ({size_mb:.1f} MB)…")
        self._add_video_bubble("me", filename)  # no Play button for sender

        # send_video() already runs in a background thread
        self.client.send_video(file_path)

    def send_file(self):
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("All files", "*.*")]
        )
        if not file_path:
            return

        filename = os.path.basename(file_path)
        self._add_system(f"Sending file: {filename}…")
        self._add_file_bubble("me", filename)
        self.client.send_file(file_path)

    # ------------------------------------------------------------------ #
    #  Receive callbacks (background thread → scheduled on UI thread)    #
    # ------------------------------------------------------------------ #

    def receive_message(self, text):
        self.window.after(0, lambda: self._add_text_bubble("friend", text))

    def receive_image(self, filename, data):
        os.makedirs("received", exist_ok=True)
        with open(os.path.join("received", filename), "wb") as f:
            f.write(data)
        self.window.after(0, lambda: self._add_image_bubble("friend", data, filename))

    def receive_video(self, filename, data):
        """Save the received video and show a Play bubble."""
        os.makedirs("received", exist_ok=True)
        save_path = os.path.join("received", filename)
        with open(save_path, "wb") as f:
            f.write(data)
        # Capture save_path in lambda so the button knows where the file is
        self.window.after(0, lambda sp=save_path, fn=filename:
                          self._add_video_bubble("friend", fn, saved_path=sp))

    def receive_file(self, filename, data):
        os.makedirs("received", exist_ok=True)
        with open(os.path.join("received", filename), "wb") as f:
            f.write(data)
        self.window.after(0, lambda: self._add_file_bubble("friend", filename, saved=True))

    # ------------------------------------------------------------------ #

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = ChatUI()
    app.run()