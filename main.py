import subprocess
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox


def run_server():
    """Launch server.py in a new console window (Windows) or background process."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    subprocess.Popen([sys.executable, "server.py"], **kwargs)
    print("[Launcher] Server started.")


def run_client():
    """Open one chat client window (ui.py)."""
    subprocess.Popen([sys.executable, "ui.py"])
    print("[Launcher] Client window opened.")



class Launcher:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Chat Launcher")
        self.window.geometry("340x310")
        self.window.configure(bg="#075e54")
        self.window.resizable(False, False)

        self.server_started = False
        self._build_ui()

    def _build_ui(self):
        tk.Label(
            self.window,
            text="💬 Python Chat",
            font=("Arial", 20, "bold"),
            fg="white", bg="#075e54"
        ).pack(pady=(28, 4))

        tk.Label(
            self.window,
            text="Project Launcher",
            font=("Arial", 11),
            fg="#b2dfdb", bg="#075e54"
        ).pack(pady=(0, 20))

        btn_cfg = dict(
            font=("Arial", 12, "bold"),
            relief="flat", cursor="hand2",
            width=24, pady=8
        )

        self.server_btn = tk.Button(
            self.window,
            text="🖥  Start Server",
            bg="#25d366", fg="white",
            command=self.start_server,
            **btn_cfg
        )
        self.server_btn.pack(pady=5)

        tk.Button(
            self.window,
            text="👤  Open Client Window",
            bg="#128c7e", fg="white",
            command=self.start_client,
            **btn_cfg
        ).pack(pady=5)

        tk.Button(
            self.window,
            text="🚀  Start Server + 2 Clients",
            bg="#ffffff", fg="#075e54",
            command=self.start_all,
            **btn_cfg
        ).pack(pady=5)

        self.status_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="#b2dfdb", bg="#075e54"
        )
        self.status_label.pack(pady=(12, 0))

    def _status(self, text):
        self.status_label.config(text=text)

    def start_server(self):
        if self.server_started:
            messagebox.showinfo("Server", "Server is already running!")
            return
        run_server()
        self.server_started = True
        self.server_btn.config(text="✅  Server Running", state="disabled", bg="#888888")
        self._status("Server running on port 5000")

    def start_client(self):
        if not self.server_started:
            messagebox.showwarning("Warning", "Start the server first!")
            return
        run_client()
        self._status("Client window opened.")

    def start_all(self):
        if not self.server_started:
            run_server()
            self.server_started = True
            self.server_btn.config(text="✅  Server Running", state="disabled", bg="#888888")

        self._status("Starting everything…")

        def _open_clients():
            time.sleep(1.2)    # Give server time to bind the port
            run_client()
            time.sleep(0.4)
            run_client()
            self.window.after(0, lambda: self._status("Server + 2 clients running ✅"))

        threading.Thread(target=_open_clients, daemon=True).start()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = Launcher()
    app.run()
