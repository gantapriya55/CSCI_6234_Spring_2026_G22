# Smart Parking Management System

A Django-based parking management system supporting **Car, Truck, Bike, and EV** vehicles with multi-floor slot allocation, dynamic pricing, and ticket management.

## Features
- **Auto Slot Assignment** – Vehicles are assigned appropriate slots based on type (Small→Bike, Medium→Car/EV, Large→Truck)
- **EV Charging Slots** – Dedicated EV slots with charger surcharge
- **Dynamic Pricing** – Configurable per-vehicle-type hourly rates
- **Parking Tickets** – UUID-based tickets with entry/exit timestamps
- **Fee Calculation** – Time-based billing with EV surcharge support
- **Multi-Floor Monitoring** – Visual grid showing slot occupancy per floor
- **Dashboard** – Real-time stats, revenue tracking, active vehicles
- **Ticket History** – Full audit trail of all parking sessions

## OOP Concepts Used
- **Inheritance** – Vehicle types extend common Vehicle model
- **Encapsulation** – Fee calculation logic encapsulated in ParkingTicket
- **Polymorphism** – Slot assignment adapts to vehicle type
- **Abstraction** – Clean separation between models, views, and templates

## Quick Start

```bash
pip install django
cd smart_parking
python manage.py migrate
python manage.py seed    # Creates 3 floors, 60 slots, pricing rules
python manage.py runserver
```

Open http://127.0.0.1:8000

## Pricing (Default)
| Vehicle | Rate/hr | EV Surcharge |
|---------|---------|--------------|
| Bike    | $2.00   | —            |
| Car     | $5.00   | —            |
| Truck   | $8.00   | —            |
| EV      | $5.00   | +$1.50/hr    |
