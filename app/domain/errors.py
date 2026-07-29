"""Errors raised when a business rule is broken.

These carry no HTTP status codes. Translating them into responses is the API
layer's job, which keeps the rules usable from anywhere else too.

They are grouped into three kinds, because those three map cleanly onto the
answer the API needs to give:

* something named in the URL does not exist
* the request parsed, but a value in it does not work
* the request is fine but clashes with what is already stored
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every business rule violation."""


class NotFoundError(DomainError):
    """Something addressed directly by the caller does not exist."""


class InvalidRequestError(DomainError):
    """The request parsed, but a value in it cannot be used."""


class ConflictError(DomainError):
    """The request clashes with the current state of the data."""


# Addressed in the URL, so a missing one means the URL is wrong.
class PatientNotFoundError(NotFoundError):
    """No patient with that id."""


class MedicationRequestNotFoundError(NotFoundError):
    """No medication request with that id."""


# Named in the body, so the request itself is the problem.
class ClinicianNotFoundError(InvalidRequestError):
    """The clinician referenced in the body does not exist."""


class MedicationNotFoundError(InvalidRequestError):
    """The medication referenced in the body does not exist."""


class InvalidDateRangeError(InvalidRequestError):
    """End date is earlier than start date."""


# Clashes with data that is already there.
class InvalidStatusTransitionError(ConflictError):
    """The requested status change is not allowed."""


class OverlappingRequestError(ConflictError):
    """An active request for the same medication already covers these dates."""
