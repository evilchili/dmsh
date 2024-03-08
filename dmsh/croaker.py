import socket
from functools import cached_property
from dataclasses import dataclass


@dataclass
class CroakerClient():
    host: str
    port: int

    @cached_property
    def playlists(self):
        return self.send("LIST").split("\n")

    def list(self, *args):
        if not args:
            return self.playlists
        return self.send(f"LIST {args[0]}")

    def play(self, *args):
        if not args:
            return "Error: Must specify the playlist to play."
        return self.send(f"PLAY {args[0]}")

    def skip(self, *args):
        return self.send("FFWD")

    def send(self, msg: str):
        BUFSIZE = 4096
        data = bytearray()
        with socket.create_connection((self.host, self.port)) as sock:
            sock.sendall(f"{msg}\n".encode())
            while True:
                buf = sock.recv(BUFSIZE)
                data.extend(buf)
                if len(buf) < BUFSIZE:
                    break
            sock.sendall(b'KTHX\n')
        return data.decode()
