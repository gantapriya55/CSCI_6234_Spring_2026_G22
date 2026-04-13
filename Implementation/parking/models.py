from django.db import models
from django.utils import timezone
import uuid
import math


class VehicleType(models.TextChoices):
    CAR = 'CAR', 'Car'
    TRUCK = 'TRUCK', 'Truck'
    BIKE = 'BIKE', 'Bike'
    EV = 'EV', 'Electric Vehicle'


SLOT_SIZE = {
    'BIKE': 'SMALL',
    'CAR': 'MEDIUM',
    'EV': 'MEDIUM',
    'TRUCK': 'LARGE',
}


class ParkingLot(models.Model):
    name = models.CharField(max_length=120)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_capacity(self):
        return ParkingSlot.objects.filter(floor__lot=self).count()

    def available_slots(self):
        return ParkingSlot.objects.filter(floor__lot=self, is_occupied=False).count()

    def occupancy_percent(self):
        total = self.total_capacity()
        if total == 0:
            return 0
        return round((total - self.available_slots()) / total * 100, 1)

    def __str__(self):
        return self.name


class Floor(models.Model):
    lot = models.ForeignKey(ParkingLot, on_delete=models.CASCADE, related_name='floors')
    floor_number = models.IntegerField()
    label = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['floor_number']
        unique_together = ['lot', 'floor_number']

    def __str__(self):
        return f"{self.lot.name} - Floor {self.floor_number}"


class SlotSize(models.TextChoices):
    SMALL = 'SMALL', 'Small (Bike)'
    MEDIUM = 'MEDIUM', 'Medium (Car / EV)'
    LARGE = 'LARGE', 'Large (Truck)'


class ParkingSlot(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='slots')
    slot_number = models.CharField(max_length=20)
    size = models.CharField(max_length=10, choices=SlotSize.choices)
    has_ev_charger = models.BooleanField(default=False)
    is_occupied = models.BooleanField(default=False)

    class Meta:
        ordering = ['floor', 'slot_number']
        unique_together = ['floor', 'slot_number']

    def __str__(self):
        tag = " [EV]" if self.has_ev_charger else ""
        return f"F{self.floor.floor_number}-{self.slot_number} [{self.get_size_display()}]{tag}"


class Vehicle(models.Model):
    license_plate = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VehicleType.choices)
    owner_name = models.CharField(max_length=120, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.license_plate} ({self.get_vehicle_type_display()})"


class PricingRule(models.Model):
    vehicle_type = models.CharField(max_length=10, choices=VehicleType.choices, unique=True)
    base_rate_per_hour = models.DecimalField(max_digits=8, decimal_places=2)
    ev_surcharge = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.get_vehicle_type_display()}: ${self.base_rate_per_hour}/hr"


class ParkingTicket(models.Model):
    ticket_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='tickets')
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='tickets')
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def duration_hours(self):
        end = self.exit_time or timezone.now()
        delta = (end - self.entry_time).total_seconds() / 3600
        return max(math.ceil(delta), 1)

    def calculate_fee(self):
        try:
            rule = PricingRule.objects.get(vehicle_type=self.vehicle.vehicle_type)
        except PricingRule.DoesNotExist:
            rule = None
        hours = self.duration_hours()
        rate = float(rule.base_rate_per_hour) if rule else 5
        total = rate * hours
        if self.slot.has_ev_charger and rule:
            total += float(rule.ev_surcharge) * hours
        return round(total, 2)

    def __str__(self):
        return f"Ticket {str(self.ticket_id)[:8]} - {self.vehicle.license_plate}"
