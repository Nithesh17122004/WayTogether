from django.utils import timezone

from .models import Notification


def notify(
    *,
    recipient,
    event_type,
    title,
    body,
    actor=None,
    booking=None,
    journey=None,
):
    if not recipient or (actor is not None and recipient.pk == actor.pk):
        return None
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        event_type=event_type,
        title=title[:160],
        body=body[:500],
        booking=booking,
        journey=journey or (booking.journey if booking else None),
    )


def notify_booking_participants(*, booking, event_type, title, body, actor):
    other = (
        booking.journey.driver
        if actor.pk == booking.passenger_id
        else booking.passenger
    )
    return notify(
        recipient=other,
        actor=actor,
        event_type=event_type,
        title=title,
        body=body,
        booking=booking,
        journey=booking.journey,
    )


def mark_notification_read(notification):
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    return notification
