"""Solution 4 - Fixed bank. All three bugs corrected."""

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

    # ------------------------------------------------------------- BUG 1 FIX
    # WAS:  acct.balance += amount          (unprotected read-modify-write)
    # Two threads read the same balance and both write back their own version;
    # one deposit is lost and money vanishes from the bank.
    def deposit(self, account_id, amount):
        acct = self.accounts[account_id]
        with acct.lock:
            acct.balance += amount

    # ------------------------------------------------------------- BUG 2 FIX
    # WAS:  the `if acct.balance >= amount` check was OUTSIDE any lock, so two
    # threads could both pass it at balance == amount and both withdraw ->
    # the account goes negative. Check and act must be one atomic unit.
    def withdraw(self, account_id, amount):
        acct = self.accounts[account_id]
        with acct.lock:
            if acct.balance >= amount:
                time.sleep(0.0001)
                acct.balance -= amount
                return True
            return False

    # ------------------------------------------------------------- BUG 3 FIX
    # WAS:  `with src.lock: with dst.lock:` -- the order depended on the
    # ARGUMENTS. transfer(0->1) takes lock0 then lock1 while transfer(1->0)
    # takes lock1 then lock0 -> circular wait -> deadlock.
    #
    # FIX: impose a GLOBAL lock order. Sorting by account id means every thread
    # always grabs the lower id first, so no cycle can form.
    def transfer(self, from_id, to_id, amount):
        if from_id == to_id:
            return False

        src = self.accounts[from_id]
        dst = self.accounts[to_id]

        first, second = sorted((src, dst), key=lambda a: a.id)
        with first.lock:
            time.sleep(0.0001)
            with second.lock:
                if src.balance >= amount:
                    src.balance -= amount
                    dst.balance += amount
                    return True
                return False

    def total_money(self):
        # Snapshot under all locks so the total is consistent even while
        # transfers are in flight. Locks taken in id order, same as transfer().
        for acct in sorted(self.accounts.values(), key=lambda a: a.id):
            acct.lock.acquire()
        try:
            return sum(a.balance for a in self.accounts.values())
        finally:
            for acct in self.accounts.values():
                acct.lock.release()


# ALTERNATIVE FIX FOR BUG 3: acquire with a timeout, release everything and
# retry on failure (see examples/11_deadlock.py demo 4). Ordering is preferred
# because it has no retry cost and cannot livelock.
