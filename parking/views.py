from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from .models import *


def dashboard(request):
    lots = ParkingLot.objects.all()
    active_tickets = ParkingTicket.objects.filter(is_active=True).select_related('vehicle', 'slot__floor')
    total_slots = ParkingSlot.objects.count()
    occupied = ParkingSlot.objects.filter(is_occupied=True).count()
    available = total_slots - occupied

    # Per-type availability
    type_stats = []
    for vtype, label in VehicleType.choices:
        needed_size = SLOT_SIZE.get(vtype, 'MEDIUM')
        qs = ParkingSlot.objects.filter(size=needed_size)
        if vtype == 'EV':
            qs = qs.filter(has_ev_charger=True)
        total_t = qs.count()
        occ_t = qs.filter(is_occupied=True).count()
        type_stats.append({'type': label, 'total': total_t, 'available': total_t - occ_t, 'occupied': occ_t})

    # Revenue today
    today = timezone.now().date()
    revenue_today = ParkingTicket.objects.filter(
        is_paid=True, exit_time__date=today
    ).aggregate(total=Sum('fee'))['total'] or 0

    context = {
        'lots': lots,
        'active_tickets': active_tickets,
        'total_slots': total_slots,
        'occupied': occupied,
        'available': available,
        'type_stats': type_stats,
        'revenue_today': revenue_today,
    }
    return render(request, 'parking/dashboard.html', context)


def park_vehicle(request):
    if request.method == 'POST':
        plate = request.POST.get('license_plate', '').upper().strip()
        vtype = request.POST.get('vehicle_type')
        owner = request.POST.get('owner_name', '')

        if not plate or not vtype:
            messages.error(request, 'License plate and vehicle type are required.')
            return redirect('park_vehicle')

        # Register or get vehicle
        vehicle, created = Vehicle.objects.get_or_create(
            license_plate=plate,
            defaults={'vehicle_type': vtype, 'owner_name': owner}
        )

        # Check if already parked
        if ParkingTicket.objects.filter(vehicle=vehicle, is_active=True).exists():
            messages.warning(request, f'{plate} is already parked!')
            return redirect('dashboard')

        # Find slot
        needed_size = SLOT_SIZE.get(vtype, 'MEDIUM')
        slot_qs = ParkingSlot.objects.filter(size=needed_size, is_occupied=False)
        if vtype == 'EV':
            slot_qs = slot_qs.filter(has_ev_charger=True)
        slot = slot_qs.first()

        if not slot:
            messages.error(request, f'No available {needed_size} slot for {vehicle.get_vehicle_type_display()}.')
            return redirect('park_vehicle')

        # Assign
        slot.is_occupied = True
        slot.save()
        ticket = ParkingTicket.objects.create(vehicle=vehicle, slot=slot)
        messages.success(request, f'Parked {plate} at {slot}. Ticket: {str(ticket.ticket_id)[:8]}')
        return redirect('dashboard')

    return render(request, 'parking/park_vehicle.html', {'vehicle_types': VehicleType.choices})


def exit_vehicle(request):
    if request.method == 'POST':
        plate = request.POST.get('license_plate', '').upper().strip()
        try:
            vehicle = Vehicle.objects.get(license_plate=plate)
        except Vehicle.DoesNotExist:
            messages.error(request, 'Vehicle not found.')
            return redirect('exit_vehicle')

        ticket = ParkingTicket.objects.filter(vehicle=vehicle, is_active=True).first()
        if not ticket:
            messages.error(request, f'{plate} has no active parking session.')
            return redirect('exit_vehicle')

        ticket.exit_time = timezone.now()
        ticket.fee = ticket.calculate_fee()
        ticket.save()

        return render(request, 'parking/payment.html', {'ticket': ticket})

    active = ParkingTicket.objects.filter(is_active=True).select_related('vehicle')
    return render(request, 'parking/exit_vehicle.html', {'active_tickets': active})


def pay_fee(request, ticket_id):
    ticket = get_object_or_404(ParkingTicket, id=ticket_id)
    ticket.is_paid = True
    ticket.is_active = False
    ticket.slot.is_occupied = False
    ticket.slot.save()
    ticket.save()
    messages.success(request, f'Payment of ${ticket.fee} received. {ticket.vehicle.license_plate} may exit.')
    return redirect('dashboard')


def monitor(request):
    floors = Floor.objects.all().prefetch_related('slots')
    floor_data = []
    for f in floors:
        slots = f.slots.all()
        floor_data.append({
            'floor': f,
            'slots': slots,
            'total': slots.count(),
            'occupied': slots.filter(is_occupied=True).count(),
            'available': slots.filter(is_occupied=False).count(),
        })
    return render(request, 'parking/monitor.html', {'floor_data': floor_data})


def manage_config(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_lot':
            name = request.POST.get('lot_name', 'New Lot')
            floors_count = int(request.POST.get('floors_count', 3))
            small_per_floor = int(request.POST.get('small_per_floor', 5))
            medium_per_floor = int(request.POST.get('medium_per_floor', 10))
            large_per_floor = int(request.POST.get('large_per_floor', 3))
            ev_per_floor = int(request.POST.get('ev_per_floor', 2))

            lot = ParkingLot.objects.create(name=name)
            for fn in range(1, floors_count + 1):
                floor = Floor.objects.create(lot=lot, floor_number=fn, label=f'Floor {fn}')
                slot_num = 1
                for _ in range(small_per_floor):
                    ParkingSlot.objects.create(floor=floor, slot_number=f'S{slot_num:03d}', size='SMALL')
                    slot_num += 1
                for _ in range(medium_per_floor):
                    ParkingSlot.objects.create(floor=floor, slot_number=f'M{slot_num:03d}', size='MEDIUM')
                    slot_num += 1
                for _ in range(large_per_floor):
                    ParkingSlot.objects.create(floor=floor, slot_number=f'L{slot_num:03d}', size='LARGE')
                    slot_num += 1
                for _ in range(ev_per_floor):
                    ParkingSlot.objects.create(floor=floor, slot_number=f'E{slot_num:03d}', size='MEDIUM', has_ev_charger=True)
                    slot_num += 1

            messages.success(request, f'Parking lot "{name}" created with {floors_count} floors.')
            return redirect('manage_config')

        elif action == 'update_pricing':
            for vtype, _ in VehicleType.choices:
                rate = request.POST.get(f'rate_{vtype}')
                ev_sur = request.POST.get(f'ev_surcharge_{vtype}', 0)
                if rate:
                    PricingRule.objects.update_or_create(
                        vehicle_type=vtype,
                        defaults={'base_rate_per_hour': rate, 'ev_surcharge': ev_sur or 0}
                    )
            messages.success(request, 'Pricing updated.')
            return redirect('manage_config')

    lots = ParkingLot.objects.all()
    pricing = PricingRule.objects.all()
    return render(request, 'parking/manage_config.html', {
        'lots': lots,
        'pricing': pricing,
        'vehicle_types': VehicleType.choices,
    })


def ticket_history(request):
    tickets = ParkingTicket.objects.all().select_related('vehicle', 'slot__floor').order_by('-entry_time')
    return render(request, 'parking/history.html', {'tickets': tickets})
