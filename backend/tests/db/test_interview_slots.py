"""Créneaux d'entretien : garanties au niveau de la base (pas de double réservation, etc.)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Appointment,
    Candidate,
    InterviewerSlot,
    Preregistration,
    User,
)
from app.models.enums import AppointmentStatus, UserRole

START = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)


@pytest.fixture
def interviewer(make_user) -> User:
    return make_user(UserRole.interviewer)


@pytest.fixture
def slot(db, interviewer) -> InterviewerSlot:
    s = InterviewerSlot(
        interviewer_id=interviewer.id, starts_at=START, ends_at=START + timedelta(minutes=30)
    )
    db.add(s)
    db.commit()
    return s


@pytest.fixture
def prereg(db, make_program) -> Preregistration:
    program = make_program()
    candidate = Candidate()
    db.add(candidate)
    db.commit()
    p = Preregistration(
        candidate_id=candidate.id,
        program_id=program.id,
        academic_year="2026-2027",
        consent_given_at=START,
        consent_version="v1",
    )
    db.add(p)
    db.commit()
    return p


def book(db, prereg, slot, status=AppointmentStatus.proposed) -> Appointment:
    a = Appointment(
        preregistration_id=prereg.id,
        interviewer_id=slot.interviewer_id,
        slot_id=slot.id,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        status=status,
    )
    db.add(a)
    db.commit()
    return a


def test_slot_must_end_after_it_starts(db, interviewer):
    db.add(InterviewerSlot(interviewer_id=interviewer.id, starts_at=START, ends_at=START))
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_interviewer_cannot_publish_same_start_twice(db, interviewer, slot):
    db.add(
        InterviewerSlot(
            interviewer_id=interviewer.id, starts_at=START, ends_at=START + timedelta(hours=1)
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_two_interviewers_can_share_a_start_time(db, make_user, slot):
    other = make_user(UserRole.interviewer)
    db.add(
        InterviewerSlot(
            interviewer_id=other.id, starts_at=START, ends_at=START + timedelta(minutes=30)
        )
    )
    db.commit()


def test_slot_cannot_be_double_booked(db, prereg, slot):
    book(db, prereg, slot)
    with pytest.raises(IntegrityError):
        book(db, prereg, slot, AppointmentStatus.confirmed)


def test_cancelling_frees_the_slot(db, prereg, slot):
    first = book(db, prereg, slot)
    first.status = AppointmentStatus.cancelled
    db.commit()
    second = book(db, prereg, slot, AppointmentStatus.confirmed)  # de nouveau réservable
    assert second.slot_id == slot.id


def test_deleting_a_slot_keeps_the_appointment(db, prereg, slot):
    appointment = book(db, prereg, slot)
    db.delete(slot)
    db.commit()
    db.refresh(appointment)
    assert appointment.slot_id is None  # l'historique du rendez-vous est conservé


def test_deleting_the_interviewer_deletes_their_slots(db, interviewer, slot):
    slot_id = slot.id
    db.delete(interviewer)
    db.commit()
    db.expire_all()
    assert db.get(InterviewerSlot, slot_id) is None
