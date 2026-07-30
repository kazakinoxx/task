"""Shared helpers for the frontend phase modules (frontend/parts/)."""

from __future__ import annotations


def hand_suffix(state) -> str:
    """'l'/'r' asset-filename suffix for the participant's preferred hand,
    used to pick hand-specific audio/images (e.g.
    `instruction-hold-key-{suffix}.mp3`, `hand-{suffix}-1-{lang}.png`)."""
    return 'l' if state.get_preferred_hand() == 'left' else 'r'
