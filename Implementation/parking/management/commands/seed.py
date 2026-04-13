from django.core.management.base import BaseCommand
from parking.models import *

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if ParkingLot.objects.exists():
            self.stdout.write("Already seeded.")
            return
        lot = ParkingLot.objects.create(name="Main Parking", address="123 University Ave")
        for fn in range(1, 4):
            floor = Floor.objects.create(lot=lot, floor_number=fn, label=f"Floor {fn}")
            n = 1
            for _ in range(5):
                ParkingSlot.objects.create(floor=floor, slot_number=f"S{n:03d}", size="SMALL"); n+=1
            for _ in range(10):
                ParkingSlot.objects.create(floor=floor, slot_number=f"M{n:03d}", size="MEDIUM"); n+=1
            for _ in range(3):
                ParkingSlot.objects.create(floor=floor, slot_number=f"L{n:03d}", size="LARGE"); n+=1
            for _ in range(2):
                ParkingSlot.objects.create(floor=floor, slot_number=f"E{n:03d}", size="MEDIUM", has_ev_charger=True); n+=1

        PricingRule.objects.create(vehicle_type="BIKE", base_rate_per_hour=2)
        PricingRule.objects.create(vehicle_type="CAR", base_rate_per_hour=5)
        PricingRule.objects.create(vehicle_type="TRUCK", base_rate_per_hour=8)
        PricingRule.objects.create(vehicle_type="EV", base_rate_per_hour=5, ev_surcharge=1.5)
        self.stdout.write(self.style.SUCCESS("Seeded: 3 floors × 20 slots + pricing"))
