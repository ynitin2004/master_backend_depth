"""Problem 2 - Pub/Sub Message Broker. Reference solution."""

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


class BrokerError(Exception): ...
class TopicNotFoundError(BrokerError): ...
class SubscriberNotFoundError(BrokerError): ...
class BrokerClosedError(BrokerError): ...


@dataclass(frozen=True)
class Message:
    offset: int
    topic: str
    payload: Any
    timestamp: float


class _Topic:
    """One append-only log, plus a CURSOR PER SUBSCRIBER.

    That split is the core insight: the messages are shared, the reading
    positions are not. A slow subscriber falls behind without blocking
    anyone else.
    """

    def __init__(self, name: str, max_messages: Optional[int] = None):
        self.name = name
        self.max_messages = max_messages
        self._log: list[Message] = []
        self._base_offset = 0                  # offset of _log[0] after trimming
        self._next_offset = 0
        self._cursors: dict[str, int] = {}     # subscriber_id -> committed offset
        self._lock = threading.RLock()

    def publish(self, payload: Any) -> int:
        with self._lock:
            message = Message(self._next_offset, self.name, payload, time.time())
            self._log.append(message)
            self._next_offset += 1

            if self.max_messages is not None and len(self._log) > self.max_messages:
                dropped = len(self._log) - self.max_messages
                del self._log[:dropped]
                self._base_offset += dropped
            return message.offset

    def subscribe(self, subscriber_id: str) -> None:
        with self._lock:
            # New subscribers start at the END: they see messages published
            # AFTER they subscribed, not the entire history.
            self._cursors.setdefault(subscriber_id, self._next_offset)

    def unsubscribe(self, subscriber_id: str) -> None:
        with self._lock:
            if self._cursors.pop(subscriber_id, None) is None:
                raise SubscriberNotFoundError(subscriber_id)

    def poll(self, subscriber_id: str, max_messages: int) -> list[Message]:
        with self._lock:
            if subscriber_id not in self._cursors:
                raise SubscriberNotFoundError(subscriber_id)
            cursor = max(self._cursors[subscriber_id], self._base_offset)
            start = cursor - self._base_offset
            # A COPY of the slice -- never hand out a live view of the log.
            return self._log[start:start + max_messages]

    def ack(self, subscriber_id: str, offset: int) -> None:
        with self._lock:
            if subscriber_id not in self._cursors:
                raise SubscriberNotFoundError(subscriber_id)
            # max(): acks may arrive out of order; the cursor must never go
            # backwards or messages get redelivered forever.
            self._cursors[subscriber_id] = max(self._cursors[subscriber_id],
                                               offset + 1)

    def lag(self, subscriber_id: str) -> int:
        with self._lock:
            return self._next_offset - self._cursors.get(subscriber_id,
                                                         self._next_offset)

    def snapshot(self) -> dict:
        with self._lock:
            return {"messages": self._next_offset,
                    "retained": len(self._log),
                    "subscribers": len(self._cursors),
                    "lag": {sid: self._next_offset - cur
                            for sid, cur in self._cursors.items()}}


class Broker:
    def __init__(self, n_delivery_workers: int = 2):
        self._topics: dict[str, _Topic] = {}
        self._lock = threading.RLock()
        self._closed = threading.Event()

        # Push delivery: publish() drops (topic, subscriber_id) onto this
        # queue and returns immediately. Delivery happens on broker threads,
        # so a slow callback never blocks the publisher.
        self._deliveries: queue.Queue = queue.Queue()
        self._callbacks: dict[tuple[str, str], Callable] = {}
        self._workers = [
            threading.Thread(target=self._delivery_loop, name=f"delivery-{i}",
                             daemon=True)
            for i in range(n_delivery_workers)
        ]
        for worker in self._workers:
            worker.start()

    # ------------------------------------------------------------- topics
    def create_topic(self, name: str, max_messages: Optional[int] = None) -> None:
        with self._lock:
            if name not in self._topics:
                self._topics[name] = _Topic(name, max_messages)

    def publish(self, topic: str, payload: Any) -> int:
        if self._closed.is_set():
            raise BrokerClosedError("broker is closed")
        offset = self._topic(topic).publish(payload)

        # Wake push subscribers. Snapshot the keys under the lock, then
        # enqueue outside it.
        with self._lock:
            waiting = [sid for (t, sid) in self._callbacks if t == topic]
        for subscriber_id in waiting:
            self._deliveries.put((topic, subscriber_id))
        return offset

    # -------------------------------------------------------- pull model
    def subscribe(self, topic: str, subscriber_id: str) -> None:
        self._topic(topic).subscribe(subscriber_id)

    def unsubscribe(self, topic: str, subscriber_id: str) -> None:
        self._topic(topic).unsubscribe(subscriber_id)
        with self._lock:
            self._callbacks.pop((topic, subscriber_id), None)

    def poll(self, topic: str, subscriber_id: str,
             max_messages: int = 10) -> list[Message]:
        return self._topic(topic).poll(subscriber_id, max_messages)

    def ack(self, topic: str, subscriber_id: str, offset: int) -> None:
        self._topic(topic).ack(subscriber_id, offset)

    # -------------------------------------------------------- push model
    def subscribe_callback(self, topic: str, subscriber_id: str,
                           callback: Callable[[Message], None]) -> None:
        self.subscribe(topic, subscriber_id)
        with self._lock:
            self._callbacks[(topic, subscriber_id)] = callback

    def _delivery_loop(self) -> None:
        while True:
            try:
                topic, subscriber_id = self._deliveries.get(timeout=0.1)
            except queue.Empty:
                if self._closed.is_set():
                    return
                continue
            try:
                self._deliver(topic, subscriber_id)
            except Exception:
                pass                     # a dead worker would stop ALL delivery
            finally:
                self._deliveries.task_done()

    def _deliver(self, topic: str, subscriber_id: str) -> None:
        with self._lock:
            callback = self._callbacks.get((topic, subscriber_id))
        if callback is None:
            return

        try:
            messages = self._topic(topic).poll(subscriber_id, max_messages=100)
        except (TopicNotFoundError, SubscriberNotFoundError):
            return

        for message in messages:
            try:
                # Callback invoked with NO broker lock held. A subscriber that
                # blocks, sleeps, or calls back into the broker must not be
                # able to freeze everything.
                callback(message)
            except Exception:
                # One bad subscriber must not break the others -- or stall
                # its own cursor forever. Ack and move on (at-most-once for
                # this message); a real system would use a dead-letter topic.
                pass
            self._topic(topic).ack(subscriber_id, message.offset)

    # ------------------------------------------------------------ admin
    def stats(self) -> dict:
        with self._lock:
            topics = dict(self._topics)
        return {"topics": {name: topic.snapshot() for name, topic in topics.items()},
                "pending_deliveries": self._deliveries.qsize(),
                "closed": self._closed.is_set()}

    def shutdown(self, timeout: float = 5.0) -> None:
        # Drain in-flight deliveries first, then stop the workers.
        deadline = time.monotonic() + timeout
        while not self._deliveries.empty() and time.monotonic() < deadline:
            time.sleep(0.01)
        self._closed.set()
        for worker in self._workers:
            worker.join(timeout=timeout)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.shutdown()

    # ---------------------------------------------------------- internal
    def _topic(self, name: str) -> _Topic:
        with self._lock:
            topic = self._topics.get(name)
            if topic is None:
                raise TopicNotFoundError(name)
            return topic


# ===========================================================================
if __name__ == "__main__":
    with Broker() as broker:
        broker.create_topic("orders")
        broker.subscribe("orders", "fast-consumer")
        broker.subscribe("orders", "slow-consumer")

        for i in range(5):
            broker.publish("orders", {"order_id": i})

        batch = broker.poll("orders", "fast-consumer", max_messages=10)
        print("fast polled :", [m.payload["order_id"] for m in batch])
        broker.ack("orders", "fast-consumer", batch[-1].offset)
        print("fast again  :", broker.poll("orders", "fast-consumer"))
        print("slow polled :", [m.payload["order_id"]
                                for m in broker.poll("orders", "slow-consumer")])
        print("-> independent cursors: the slow consumer still sees everything")

        received = []
        broker.subscribe_callback("orders", "pusher", received.append)
        broker.publish("orders", {"order_id": 99})
        time.sleep(0.3)
        print("push delivery:", [m.payload["order_id"] for m in received])
        print("stats:", broker.stats()["topics"]["orders"])
