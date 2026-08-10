"""Problem 5 - Parking Lot. Reference solution."""

import itertools
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class ParkingError(Exception): ...
class LotFullError(ParkingError): ...
class TicketNotFoundError(ParkingError): ...
class AlreadyParkedError(ParkingError): ...


class SpotSize(IntEnum):
    """IntEnum so `spot.size >= vehicle.size` expresses 'fits' directly."""
    SMALL = 1
    MEDIUM = 2
    LARGE = 3


@dataclass(frozen=True)
class Vehicle:
    license_plate: str
    size: SpotSize


@dataclass(frozen=True)
class Ticket:
    id: str
    license_plate: str
    spot_id: str
    floor: int
    entry_time: float


@dataclass(frozen=True)
class Receipt:
    ticket_id: str
    spot_id: str
    license_plate: str
    duration_seconds: float
    fee: float


@dataclass
class Spot:
    id: str
    floor: int
    size: SpotSize
    occupied_by: Optional[str] = None      # license plate

    @property
    def is_free(self) -> bool:
        return self.occupied_by is None


# =============================================================== pricing
class PricingStrategy(ABC):
    """The problem hints at variable pricing -> that's the ABC."""

    @abstractmethod
    def compute(self, size: SpotSize, duration_seconds: float) -> float: ...


class HourlyPricing(PricingStrategy):
    def __init__(self, rates: Optional[dict] = None, free_minutes: float = 0.0):
        self._rates = rates or {SpotSize.SMALL: 10.0,
                                SpotSize.MEDIUM: 20.0,
                                SpotSize.LARGE: 40.0}
        self._free_seconds = free_minutes * 60

    def compute(self, size: SpotSize, duration_seconds: float) -> float:
        # Within the grace period -> free. Otherwise bill a MINIMUM of one
        # hour and round part-hours up, which is what real lots do.
        if duration_seconds <= self._free_seconds:
            return 0.0
        billable = duration_seconds - self._free_seconds
        hours = max(1, -(-int(billable) // 3600))     # ceil division
        return round(self._rates[size] * hours, 2)


class FlatRatePricing(PricingStrategy):
    def __init__(self, rate: float = 50.0):
        self._rate = rate

    def compute(self, size: SpotSize, duration_seconds: float) -> float:
        return self._rate


# ============================================================== the lot
class ParkingLot:
    def __init__(self, layout: dict, pricing: Optional[PricingStrategy] = None):
        """layout: {floor_number: {SpotSize.SMALL: count, ...}}"""
        self._pricing = pricing or HourlyPricing()

        self._spots: dict[str, Spot] = {}
        # Free spots indexed by (floor, size) so allocation is O(1) instead
        # of scanning every spot. Lowest floor first is just sorted order.
        self._free: dict[tuple[int, SpotSize], list[str]] = {}

        for floor in sorted(layout):
            for size in sorted(layout[floor]):
                for i in range(layout[floor][size]):
                    spot_id = f"F{floor}-{size.name[0]}{i}"
                    self._spots[spot_id] = Spot(spot_id, floor, size)
                    self._free.setdefault((floor, size), []).append(spot_id)

        self._tickets: dict[str, Ticket] = {}
        self._by_plate: dict[str, str] = {}      # plate -> spot_id
        self._ids = itertools.count(1)

        # ONE lock over all allocation state. Allocation is a check-then-act
        # (find a free spot, then claim it) and splitting those two steps is
        # exactly how two cars get assigned the same spot.
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- park
    def park(self, vehicle: Vehicle) -> Ticket:
        now = time.time()
        with self._lock:
            if vehicle.license_plate in self._by_plate:
                raise AlreadyParkedError(
                    f"{vehicle.license_plate} is already parked at "
                    f"{self._by_plate[vehicle.license_plate]}")

            spot_id = self._find_free_spot(vehicle.size)
            if spot_id is None:
                raise LotFullError(
                    f"no free spot fits a {vehicle.size.name} vehicle")

            # FIND and CLAIM inside the same lock acquisition. This is the
            # entire concurrency story of the problem.
            spot = self._spots[spot_id]
            spot.occupied_by = vehicle.license_plate
            self._free[(spot.floor, spot.size)].remove(spot_id)

            ticket = Ticket(id=f"T{next(self._ids)}",
                            license_plate=vehicle.license_plate,
                            spot_id=spot_id, floor=spot.floor, entry_time=now)
            self._tickets[ticket.id] = ticket
            self._by_plate[vehicle.license_plate] = spot_id
            return ticket

    def _find_free_spot(self, size: SpotSize) -> Optional[str]:
        """Caller holds the lock.

        A vehicle fits its own size OR LARGER. Try the exact size first so a
        small car doesn't consume a large spot while smalls are available.
        Within a size, prefer the lowest floor.
        """
        for candidate_size in sorted(SpotSize):
            if candidate_size < size:
                continue
            for (floor, spot_size), free_ids in sorted(self._free.items()):
                if spot_size is candidate_size and free_ids:
                    return free_ids[0]
        return None

    # -------------------------------------------------------------- unpark
    def unpark(self, ticket_id: str) -> Receipt:
        now = time.time()
        with self._lock:
            ticket = self._tickets.pop(ticket_id, None)
            if ticket is None:
                raise TicketNotFoundError(ticket_id)

            spot = self._spots[ticket.spot_id]
            spot.occupied_by = None
            self._free[(spot.floor, spot.size)].append(spot.id)
            self._by_plate.pop(ticket.license_plate, None)
            duration = now - ticket.entry_time
            size = spot.size

        # Pricing computed OUTSIDE the lock: it's caller-supplied strategy
        # code and you never run unknown code while holding a lock.
        fee = self._pricing.compute(size, duration)
        return Receipt(ticket_id=ticket.id, spot_id=ticket.spot_id,
                       license_plate=ticket.license_plate,
                       duration_seconds=duration, fee=fee)

    # -------------------------------------------------------------- queries
    def availability(self) -> dict:
        with self._lock:
            counts = {size: 0 for size in SpotSize}
            for (_floor, size), free_ids in self._free.items():
                counts[size] += len(free_ids)
            return counts

    def availability_by_floor(self) -> dict:
        with self._lock:
            result: dict = {}
            for (floor, size), free_ids in self._free.items():
                result.setdefault(floor, {})[size.name] = len(free_ids)
            return result

    def find_vehicle(self, license_plate: str) -> Optional[str]:
        with self._lock:
            return self._by_plate.get(license_plate)

    def occupancy(self) -> dict:
        with self._lock:
            total = len(self._spots)
            free = sum(len(ids) for ids in self._free.values())
            return {"total": total, "occupied": total - free, "free": free,
                    "active_tickets": len(self._tickets)}


# ===========================================================================
if __name__ == "__main__":
    lot = ParkingLot(
        layout={
            0: {SpotSize.SMALL: 2, SpotSize.MEDIUM: 2},
            1: {SpotSize.MEDIUM: 1, SpotSize.LARGE: 1},
        },
        pricing=HourlyPricing(),
    )
    print("initial availability:", {s.name: n for s, n in lot.availability().items()})

    bike = lot.park(Vehicle("KA-01-1111", SpotSize.SMALL))
    car = lot.park(Vehicle("KA-02-2222", SpotSize.MEDIUM))
    print(f"\nparked bike -> {bike.spot_id} (floor {bike.floor})")
    print(f"parked car  -> {car.spot_id} (floor {car.floor})")
    print("availability:", {s.name: n for s, n in lot.availability().items()})
    print("by floor    :", lot.availability_by_floor())
    print("find KA-02  :", lot.find_vehicle("KA-02-2222"))

    try:
        lot.park(Vehicle("KA-01-1111", SpotSize.SMALL))
    except AlreadyParkedError as exc:
        print("duplicate   :", type(exc).__name__)

    time.sleep(0.05)
    receipt = lot.unpark(car.id)
    print(f"\nunparked    : fee={receipt.fee} "
          f"duration={receipt.duration_seconds:.3f}s (minimum 1 hour billed)")

    free_lot = ParkingLot(layout={0: {SpotSize.SMALL: 1}},
                          pricing=HourlyPricing(free_minutes=15))
    t = free_lot.park(Vehicle("KA-09-9999", SpotSize.SMALL))
    print(f"grace period: fee={free_lot.unpark(t.id).fee} (within 15 free minutes)")

    print("\n--- concurrency: 20 threads, 6 spots ---")
    lot2 = ParkingLot(layout={0: {SpotSize.MEDIUM: 6}})
    tickets, rejected = [], []
    lock = threading.Lock()

    def try_park(i):
        try:
            ticket = lot2.park(Vehicle(f"CAR-{i}", SpotSize.MEDIUM))
            with lock:
                tickets.append(ticket)
        except LotFullError:
            with lock:
                rejected.append(i)

    threads = [threading.Thread(target=try_park, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()

    spots_used = [t.spot_id for t in tickets]
    print(f"parked      : {len(tickets)} (capacity 6)")
    print(f"rejected    : {len(rejected)}")
    print(f"unique spots: {len(set(spots_used))} <- must equal parked count")
    print(f"no double-allocation: {len(set(spots_used)) == len(spots_used)}")
    print("occupancy   :", lot2.occupancy())
