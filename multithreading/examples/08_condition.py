"""
Module 8 - Condition: wait for an arbitrary state change.

Run:  python multithreading/examples/08_condition.py

A Condition = a Lock + a waiting room.
  cond.wait()        releases the lock, sleeps, re-acquires the lock on wake
  cond.notify()      wake ONE waiter
  cond.notify_all()  wake ALL waiters
You must hold the lock to call any of them.
"""

import threading
import time


def demo_1_producer_consumer():
    print("\n--- 1. Producer/consumer built by hand with a Condition ---")
    buffer = []
    MAX = 3
    cond = threading.Condition()
    DONE = object()

    def producer():
        for i in range(6):
            with cond:
                # Wait while the buffer is FULL. while-loop, not if.
                while len(buffer) >= MAX:
                    print(f"    [producer] buffer full, waiting")
                    cond.wait()
                buffer.append(i)
                print(f"    [producer] put {i}  buffer={buffer}")
                cond.notify_all()        # tell consumers there is data
            time.sleep(0.05)
        with cond:
            buffer.append(DONE)
            cond.notify_all()

    def consumer():
        while True:
            with cond:
                while not buffer:        # wait while EMPTY
                    cond.wait()
                item = buffer.pop(0)
                if item is DONE:
                    cond.notify_all()    # let other consumers see it too
                    return
                print(f"    [consumer] got {item}  buffer={buffer}")
                cond.notify_all()        # tell producer there is space
            time.sleep(0.12)             # consumer is slower than producer

    p = threading.Thread(target=producer, name="producer")
    c = threading.Thread(target=consumer, name="consumer")
    p.start(); c.start()
    p.join();  c.join()
    print("  Note the producer BLOCKED when the buffer hit 3 -> backpressure.")
    print("  (queue.Queue does all of this for you -- Module 10. This is the guts.)")


def demo_2_why_while_not_if():
    print("\n--- 2. Why wait() must be in a `while`, never an `if` ---")
    print("""
    Two consumers are waiting. Producer adds ONE item and calls notify_all().

      with cond:                with cond:
          if not buffer:  <-- BUG   while not buffer:  <-- CORRECT
              cond.wait()               cond.wait()
          buffer.pop()              buffer.pop()

    Both consumers wake. Consumer A re-acquires the lock first and pops the item.
    Consumer B then gets the lock -- and with `if`, it proceeds straight to
    buffer.pop() on an EMPTY list -> IndexError.

    With `while`, B re-checks the condition, sees it's still empty, and waits again.

    Also: the language explicitly permits SPURIOUS WAKEUPS (wait() returning with
    nothing changed). `while` handles that for free. There is no correct use of
    `if` here.""")


def demo_3_wait_for():
    print("\n--- 3. wait_for(predicate): the while-loop, done for you ---")
    state = {"stage": 0}
    cond = threading.Condition()

    def waiter(target):
        with cond:
            # equivalent to: while state["stage"] < target: cond.wait()
            cond.wait_for(lambda: state["stage"] >= target)
            print(f"    waiter-for-stage-{target} released (stage={state['stage']})")

    threads = [threading.Thread(target=waiter, args=(n,)) for n in (1, 2, 3)]
    for t in threads: t.start()

    for stage in (1, 2, 3):
        time.sleep(0.25)
        with cond:
            state["stage"] = stage
            print(f"  [main] stage -> {stage}")
            cond.notify_all()

    for t in threads: t.join()
    print("  wait_for() also takes a timeout and returns the predicate's last value.")


def demo_4_notify_vs_notify_all():
    print("\n--- 4. notify() vs notify_all() ---")
    cond = threading.Condition()
    woke = []
    ready = {"go": False}

    def waiter(i):
        with cond:
            cond.wait_for(lambda: ready["go"])
            woke.append(i)

    threads = [threading.Thread(target=waiter, args=(i,)) for i in range(3)]
    for t in threads: t.start()
    time.sleep(0.2)

    with cond:
        ready["go"] = True
        cond.notify()                    # wake exactly ONE
    time.sleep(0.3)
    print(f"  after notify()     : {len(woke)} thread(s) proceeded -> {woke}")

    with cond:
        cond.notify_all()                # wake the rest
    for t in threads: t.join()
    print(f"  after notify_all() : {len(woke)} thread(s) proceeded -> {woke}")
    print("""
  notify()     -> cheaper, but if the woken thread can't actually proceed,
                  nobody else gets woken and you hang. Use only when every
                  waiter is interchangeable and one item = one waiter.
  notify_all() -> safe default. Use it unless you've proven notify() is correct.""")


if __name__ == "__main__":
    demo_1_producer_consumer()
    demo_2_why_while_not_if()
    demo_3_wait_for()
    demo_4_notify_vs_notify_all()
