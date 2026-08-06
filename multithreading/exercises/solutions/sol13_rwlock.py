"""Solution 13 - Read-write lock, writer-preferring (no writer starvation)."""

import threading
from contextlib import contextmanager


class ReadWriteLock:
    def __init__(self):
        self._cond = threading.Condition()
        self._readers = 0            # readers currently INSIDE
        self._writer = False         # a writer is currently INSIDE
        self._waiting_writers = 0    # <- the anti-starvation counter

    @contextmanager
    def read_lock(self):
        with self._cond:
            # The `not self._waiting_writers` clause is what makes this
            # writer-preferring. Without it, a steady stream of readers keeps
            # self._readers above zero forever and the writer never runs.
            self._cond.wait_for(
                lambda: not self._writer and self._waiting_writers == 0)
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()   # last reader out wakes the writer

    @contextmanager
    def write_lock(self):
        with self._cond:
            self._waiting_writers += 1        # announce intent IMMEDIATELY,
                                              # before waiting -- this is what
                                              # blocks incoming new readers
            try:
                self._cond.wait_for(
                    lambda: not self._writer and self._readers == 0)
                self._writer = True
            finally:
                self._waiting_writers -= 1
        try:
            yield
        finally:
            with self._cond:
                self._writer = False
                self._cond.notify_all()

    @property
    def state(self):
        with self._cond:
            return {"readers": self._readers, "writer": self._writer,
                    "waiting_writers": self._waiting_writers}


# ---------------------------------------------------------------------------
# READER-PREFERRING VARIANT (simpler, but writers CAN starve). Shown so you
# can name the trade-off in an interview.
class ReaderPreferringRWLock:
    def __init__(self):
        self._cond = threading.Condition()
        self._readers = 0
        self._writer = False

    @contextmanager
    def read_lock(self):
        with self._cond:
            self._cond.wait_for(lambda: not self._writer)   # ignores writers
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()

    @contextmanager
    def write_lock(self):
        with self._cond:
            self._cond.wait_for(lambda: not self._writer and self._readers == 0)
            self._writer = True
        try:
            yield
        finally:
            with self._cond:
                self._writer = False
                self._cond.notify_all()


# INTERVIEW TALKING POINTS:
#
# * Reader-preferring  : max read throughput, writers may starve.
# * Writer-preferring  : writers bounded (this implementation), readers wait
#                        a little longer. Usually what you want.
# * Fair/FIFO          : queue every request in arrival order. No starvation
#                        either way, lowest throughput.
#
# * When is an RWLock worth it? Only when reads VASTLY outnumber writes AND
#   the critical section is long enough to matter. The bookkeeping here costs
#   more than a plain Lock, so for short critical sections a plain Lock wins.
#   Measure before reaching for this.
#
# * Not reentrant: a thread holding the read lock that asks for the write lock
#   deadlocks (it is waiting for its own reader count to hit zero). Never nest
#   these.
#
# * Python has no RWLock in the standard library -- this is exactly why it is
#   such a common interview question.
