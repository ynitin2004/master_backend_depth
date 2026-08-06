"""
Problem 4 - Fix the buggy bank.  (Tier 2, Modules 4-5, 11)

This code has THREE concurrency bugs. Find and fix all three.
Do not change the public API (class name, method names, signatures).

  Bug 1: a lost-update race        -> the total money in the bank changes
  Bug 2: a check-then-act race     -> an account can go negative
  Bug 3: a deadlock in transfer()  -> two opposite transfers hang forever

The checker asserts: money is conserved, no balance is ever negative, and 200
concurrent transfers finish within 10 seconds.

Check:  python multithreading/exercises/check.py 4
"""

import threading
import time


class Account:
    def __init__(self, account_id, balance):
        self.id = account_id
        self.balance = balance
        self.lock = threading.Lock()


class Bank:
    def __init__(self, n_accounts=5, starting_balance=1000):
        self.accounts = {i: Account(i, starting_balance) for i in range(n_accounts)}

    def deposit(self, account_id, amount):
        acct = self.accounts[account_id]
        # BUG 1 is here.
        acct.balance += amount

    def withdraw(self, account_id, amount):
        acct = self.accounts[account_id]
        # BUG 2 is here.
        if acct.balance >= amount:
            time.sleep(0.0001)          # widens the window; do NOT delete this
            acct.balance -= amount
            return True
        return False

    def transfer(self, from_id, to_id, amount):
        src = self.accounts[from_id]
        dst = self.accounts[to_id]
        # BUG 3 is here.
        with src.lock:
            time.sleep(0.0001)          # widens the window; do NOT delete this
            with dst.lock:
                if src.balance >= amount:
                    src.balance -= amount
                    dst.balance += amount
                    return True
                return False

    def total_money(self):
        return sum(a.balance for a in self.accounts.values())


if __name__ == "__main__":
    bank = Bank()
    start = bank.total_money()

    ts = [threading.Thread(target=bank.transfer, args=(i % 5, (i + 1) % 5, 50))
          for i in range(50)]
    for t in ts: t.start()
    for t in ts: t.join(timeout=5)

    print(f"alive threads (should be 0): {sum(t.is_alive() for t in ts)}")
    print(f"total money: {start} -> {bank.total_money()}")
