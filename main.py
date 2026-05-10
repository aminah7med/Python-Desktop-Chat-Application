import subprocess
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox


def run_server():
    """Launch server.py in a subprocess."""
    subprocess.Popen(
        [sys.executable, "server.py"],
        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    )
    print("[Main] Server started.")


def run_client():
    """Launch ui.py in a subprocess (each call = one client window)."""
    subprocess.Popen([sys.executable, "ui.py"])
    print("[Main] Client window opened.")


# ------------------------------------------------------------------ #
#  Launcher GUI                                                        #
# ------------------------------------------------------------------ #

class Launcher:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Chat Launcher")
        self.window.geometry("340x300")
        self.window.configure(bg="#075e54")
        self.window.resizable(False, False)

        self.server_started = False

        self._build_ui()

    def _build_ui(self):
        # Title
        tk.Label(
            self.window,
            text="💬 Python Chat",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#075e54"
        ).pack(pady=(30, 4))

        tk.Label(
            self.window,
            text="Project Launcher",
            font=("Arial", 11),
            fg="#b2dfdb",
            bg="#075e54"
        ).pack(pady=(0, 24))

        # Server button
        self.server_btn = tk.Button(
            self.window,
            text="🖥  Start Server",
            font=("Arial", 12, "bold"),
            bg="#25d366",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=22,
            pady=8,
            command=self.start_server
        )
        self.server_btn.pack(pady=6)

        # Client button
        tk.Button(
            self.window,
            text="👤  Open Client Window",
            font=("Arial", 12, "bold"),
            bg="#128c7e",
            fg="white",
            relief="flat",
            cursor="hand2",
            width=22,
            pady=8,
            command=self.start_client
        ).pack(pady=6)

        # Both button
        tk.Button(
            self.window,
            text="🚀  Start Server + 2 Clients",
            font=("Arial", 12, "bold"),
            bg="#ffffff",
            fg="#075e54",
            relief="flat",
            cursor="hand2",
            width=22,
            pady=8,
            command=self.start_all
        ).pack(pady=6)

        # Status label
        self.status = tk.Label(
            self.window,
            text="",
            font=("Arial", 9),
            fg="#b2dfdb",
            bg="#075e54"
        )
        self.status.pack(pady=(10, 0))

    def _set_status(self, text):
        self.status.config(text=text)

    def start_server(self):
        if self.server_started:
            messagebox.showinfo("Server", "Server is already running!")
            return

        run_server()
        self.server_started = True
        self.server_btn.config(text="✅  Server Running", state="disabled", bg="#888888")
        self._set_status("Server is running on port 5000")

    def start_client(self):
        if not self.server_started:
            messagebox.showwarning("Warning", "Start the server first!")
            return
        run_client()
        self._set_status("Client window opened.")

    def start_all(self):
        """Start server then open 2 client windows with a small delay."""
        if not self.server_started:
            run_server()
            self.server_started = True
            self.server_btn.config(text="✅  Server Running", state="disabled", bg="#888888")

        self._set_status("Starting everything…")

        def _delayed_clients():
            time.sleep(1.2)           # give server time to bind
            run_client()
            time.sleep(0.4)
            run_client()
            self.window.after(0, lambda: self._set_status("Server + 2 clients running ✅"))

        threading.Thread(target=_delayed_clients, daemon=True).start()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = Launcher()
    app.run()
