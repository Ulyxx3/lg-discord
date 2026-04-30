"""
roles/bear_tamer.py — Le Montreur d'Ours.
Chaque matin, si l'un de ses voisins est un Loup-Garou, l'ours grogne.
Le bot annonce le grognement dans le salon du village.
"""

from __future__ import annotations

from roles.base_role import BaseRole


class BearTamer(BaseRole):
    name        = "Montreur d'Ours"
    team        = "village"
    description = "Chaque matin, si un de vos voisins est un loup, l'ours grogne dans le village."
    emoji       = "🐻"
    night_order = None
    extension   = "nouvelle_lune"
    # La logique de grognement est dans day_phase.py (vérification post-nuit)
