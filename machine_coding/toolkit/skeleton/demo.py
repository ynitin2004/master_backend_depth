"""File 6 of 6. Two minutes. CREATE AND RUN THIS AT MINUTE 12.

This is your UI -- the interviewer will run exactly this file. Make the
output sectioned and readable so your features are VISIBLE, not merely
present.

Run:  python demo.py
"""

import threading

from service import Priority, Service, Status
from service.exceptions import InvalidStateError, ServiceError


def section(title):
    print(f"\n{'=' * 62}\n  {title}\n{'=' * 62}")


def main():
    service = Service()

    # ---------------------------------------------------------------------
    section("1. Create entities")
    for name, priority in [("deploy", Priority.HIGH),
                           ("backup", Priority.LOW),
                           ("report", Priority.MEDIUM)]:
        entity = service.create(name, priority)
        print(f"  created {entity.id:8} name={entity.name:8} "
              f"priority={entity.priority.name:6} status={entity.status.value}")

    # ---------------------------------------------------------------------
    section("2. State transitions")
    service.activate("ent-1")
    service.complete("ent-1")
    print(f"  ent-1 -> {service.get('ent-1').status.value}")

    service.cancel("ent-2")
    print(f"  ent-2 -> {service.get('ent-2').status.value}")

    # ---------------------------------------------------------------------
    section("3. Illegal transitions are rejected")
    for entity_id, action in [("ent-1", "activate"), ("ent-2", "cancel")]:
        try:
            getattr(service, action)(entity_id)
            print(f"  {action}({entity_id}) unexpectedly succeeded")
        except InvalidStateError as exc:
            print(f"  {action}({entity_id}) -> InvalidStateError: {exc}")

    try:
        service.get("nope")
    except ServiceError as exc:
        print(f"  get('nope')          -> {type(exc).__name__}: {exc}")

    # ---------------------------------------------------------------------
    section("4. Queries")
    print(f"  all       : {[e.id for e in service.list()]}")
    print(f"  completed : {[e.id for e in service.list(Status.COMPLETED)]}")
    print(f"  stats     : {service.stats()}")

    # ---------------------------------------------------------------------
    section("5. Concurrent creates (thread safety)")
    errors = []

    def spam(n):
        try:
            for i in range(50):
                service.create(f"worker{n}-item{i}")
        except Exception as exc:          # noqa: BLE001 - demo only
            errors.append(exc)

    threads = [threading.Thread(target=spam, args=(i,)) for i in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()

    print(f"  8 threads x 50 creates")
    print(f"  errors      : {len(errors)}")
    print(f"  total       : {service.stats()['total']} (expected 403)")
    print(f"  unique ids  : {len({e.id for e in service.list()})} (no duplicates)")

    service.shutdown()
    print("\n  shutdown complete")


if __name__ == "__main__":
    main()
