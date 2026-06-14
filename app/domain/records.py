"""Helpers for reading member-like records without depending on a framework."""

from collections.abc import Iterable, Mapping
from typing import Any

MISSING = object()


def value(record: Any, *names: str, default: Any = None) -> Any:
    """Return the first present field from a dict-like or object-like record."""

    for name in names:
        if isinstance(record, Mapping) and name in record:
            return record[name]
        attr = getattr(record, name, MISSING)
        if attr is not MISSING:
            return attr
    return default


def record_id(record: Any) -> Any:
    return value(record, "id")


def active(record: Any) -> bool:
    """A record is active when it has no deleted_at value."""

    return not bool(value(record, "deleted_at", default=None))


def members_for_family(members: Iterable[Any], family_id: Any) -> tuple[Any, ...]:
    return tuple(
        member for member in members if value(member, "family_id", "fid", default=None) == family_id and active(member)
    )


def family_lookup(families: Mapping[Any, Any] | Iterable[Any] | None) -> dict[Any, Any]:
    if families is None:
        return {}
    if isinstance(families, Mapping):
        return dict(families)
    return {
        value(family, "id", "family_id"): family
        for family in families
        if value(family, "id", "family_id", default=None) is not None
    }
