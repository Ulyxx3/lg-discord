"""
roles/little_girl.py — La Petite Fille.
Elle peut espionner les loups la nuit (si elle est "découverte" par un loup,
elle est éliminée à la place de la victime choisie).
En pratique : elle peut lire le salon #loups-garous pendant leur tour.
"""

from __future__ import annotations

from roles.base_role import BaseRole


class LittleGirl(BaseRole):
    name        = "Petite Fille"
    team        = "village"
    description = "La nuit, vous pouvez espionner les loups. Si vous êtes découverte, vous mourez à leur place."
    emoji       = "👧"
    night_order = None
    extension   = "nouvelle_lune"
    # La mécanique d'espionnage est gérée dynamiquement dans night_phase.py :
    # pendant le tour des loups, le salon loups_text est temporairement lisible
    # par la Petite Fille (avec une probabilité de se faire prendre = option config).
