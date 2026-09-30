"""Fail closed on accidental external I/O in the trusted test process."""

import os
from pathlib import Path
import sys


class OfflineViolation(BaseException):
    """Not swallowed by the application's broad Exception fallback handlers."""


def deny(*args, **kwargs):
    # Never include arguments: a client call may contain credentials.
    raise OfflineViolation("External I/O or model/client construction is disabled in tests")


class WriteGuard:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.active = True

    def check_path(self, path):
        if isinstance(path, int) or path is None:
            return  # Existing file descriptors (pytest capture/stdout).
        resolved = Path(os.fsdecode(path)).resolve()
        # Pytest's logging handler opens the OS null sink; it is not a store.
        if (os.name == "nt" and resolved.name.lower() == "nul") or resolved == Path(os.devnull).resolve():
            return
        if not resolved.is_relative_to(self.root):
            raise OfflineViolation("Test attempted a write outside its temporary tree")

    def __call__(self, event, args):
        if not self.active:
            return
        if event == "sqlite3.connect" and args[0] != ":memory:":
            self.check_path(args[0])
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo",
                     "socket.sendto", "subprocess.Popen", "os.system", "os.startfile",
                     "os.posix_spawn", "os.spawn", "os.exec"}:
            deny()
        if event == "open":
            path, mode, flags = args
            if (mode and any(c in mode for c in "wax+")) or (
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            ):
                self.check_path(path)
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.truncate"}:
            self.check_path(args[0])
        elif event in {"os.rename", "os.link", "os.symlink"}:
            self.check_path(args[0])
            self.check_path(args[1])

    def install(self):
        sys.addaudithook(self)
