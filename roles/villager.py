"""
roles/villager.py — Le Villageois (rôle passif).
"""

from roles.base_role import BaseRole


class Villager(BaseRole):
    name        = "Villageois"
    team        = "village"
    description = "Simple villageois. Débattez et votez pour éliminer les loups !"
    emoji       = "👨‍🌾"
    night_order = None  # Pas d'action nocturne
    extension   = "base"
