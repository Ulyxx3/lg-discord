"""
core/game_config.py — Configuration d'une partie (extensions, deck de rôles, timers).
Géré via /lg config avant le lancement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import config as C

if TYPE_CHECKING:
    pass


# Liste des extensions gérées
EXTENSIONS: dict[str, str] = {
    "base":          "Jeu de Base",
    "nouvelle_lune": "Nouvelle Lune",
}


# Ordre officiel d'apparition des rôles la nuit (selon règles Thiercelieux)
# Plus le chiffre est petit, plus le rôle agit tôt dans la nuit.
NIGHT_ORDER: dict[str, int] = {
    "Voleur":              1,
    "Cupidon":             2,
    "Les Deux Sœurs":      3,
    "Les Trois Frères":    4,
    "Voyante":             5,
    "Renard":              6,
    "Joueur de Flûte":     7,
    "Loup-Garou":          8,
    "Grand Méchant Loup":  8,   # Agit en même temps que les loups
    "Village Infect":      8,   # Idem
    "Chien-Loup":          8,   # Idem
    "Sorcière":            9,
    "Salvateur":           10,  # note: certaines variantes le placent avant les loups
    "Chasseur":            99,  # Réactif (uniquement si mort)
    "Enfant Sauvage":      0,   # Début de partie seulement (1ère nuit)
    "Acteur":              0,
}

# Rôles disponibles par extension, avec leur quantité par défaut (min, max)
ROLES_BY_EXTENSION: dict[str, list[dict]] = {
    "base": [
        {"name": "Villageois",  "min": 1, "max": 20, "default": 4, "team": "village"},
        {"name": "Loup-Garou",  "min": 1, "max": 10, "default": 2, "team": "loups"},
        {"name": "Voyante",     "min": 0, "max": 1,  "default": 1, "team": "village"},
        {"name": "Sorcière",    "min": 0, "max": 1,  "default": 1, "team": "village"},
        {"name": "Chasseur",    "min": 0, "max": 1,  "default": 1, "team": "village"},
        {"name": "Cupidon",     "min": 0, "max": 1,  "default": 1, "team": "village"},
        {"name": "Voleur",      "min": 0, "max": 1,  "default": 0, "team": "village"},
    ],
    "nouvelle_lune": [
        {"name": "Salvateur",          "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Ancien",             "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Bouc Émissaire",     "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Idiot du Village",   "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Les Deux Sœurs",     "min": 0, "max": 1,  "default": 0, "team": "village"},  # compte pour 2 cartes
        {"name": "Les Trois Frères",   "min": 0, "max": 1,  "default": 0, "team": "village"},  # compte pour 3 cartes
        {"name": "Renard",             "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Montreur d'Ours",    "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Juge Bègue",         "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Servante Rusée",     "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Petite Fille",       "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Enfant Sauvage",     "min": 0, "max": 1,  "default": 0, "team": "village"},
        {"name": "Chien-Loup",         "min": 0, "max": 1,  "default": 0, "team": "neutre"},
        {"name": "Grand Méchant Loup", "min": 0, "max": 1,  "default": 0, "team": "loups"},
        {"name": "Village Infect",     "min": 0, "max": 1,  "default": 0, "team": "loups"},
        {"name": "Ange",               "min": 0, "max": 1,  "default": 0, "team": "neutre"},
        {"name": "Joueur de Flûte",    "min": 0, "max": 1,  "default": 0, "team": "neutre"},
        {"name": "Acteur",             "min": 0, "max": 1,  "default": 0, "team": "village"},
    ],
}


@dataclass
class GameConfig:
    """
    Configuration complète d'une partie.
    Construite via /lg config et validée avant /lg start.
    """
    enabled_extensions: set[str] = field(default_factory=lambda: {"base"})

    # deck = {nom_du_role: nombre_de_cartes_dans_le_deck}
    deck: dict[str, int] = field(default_factory=dict)

    # Timers personnalisables (en secondes)
    debate_duration:  int = C.PHASE_TIMEOUT_DAY_DEBATE
    night_role_timeout: int = C.PHASE_TIMEOUT_NIGHT_ROLE
    wolves_timeout:   int = C.PHASE_TIMEOUT_WOLVES
    vote_timeout:     int = C.PHASE_TIMEOUT_DAY_VOTE

    # Règles optionnelles
    first_night_only_thief: bool = True    # Le Voleur joue uniquement la 1ère nuit
    first_night_only_cupid: bool = True    # Cupidon joue uniquement la 1ère nuit

    def __post_init__(self):
        if not self.deck:
            self._load_defaults()

    def _load_defaults(self):
        """Charge le deck par défaut selon les extensions activées."""
        self.deck = {}
        for ext in self.enabled_extensions:
            for role_def in ROLES_BY_EXTENSION.get(ext, []):
                if role_def["default"] > 0:
                    self.deck[role_def["name"]] = role_def["default"]

    def total_cards(self) -> int:
        """Nombre total de cartes dans le deck."""
        total = 0
        for name, count in self.deck.items():
            # Les Deux Sœurs = 2 cartes, Les Trois Frères = 3 cartes
            if name == "Les Deux Sœurs":
                total += 2 * count
            elif name == "Les Trois Frères":
                total += 3 * count
            else:
                total += count
        return total

    def validate(self, player_count: int) -> list[str]:
        """
        Valide la config pour un nombre de joueurs donné.
        Retourne une liste d'erreurs (vide = OK).
        """
        errors: list[str] = []
        total = self.total_cards()
        if total < player_count:
            errors.append(
                f"Le deck contient {total} cartes pour {player_count} joueurs. "
                f"Ajoutez {player_count - total} Villageois."
            )
        elif total > player_count:
            # Si on a un Voleur, on peut avoir 2 cartes de plus
            has_thief = self.deck.get("Voleur", 0) > 0
            allowed_extra = 2 if has_thief else 0
            if total - player_count > allowed_extra:
                errors.append(
                    f"Le deck contient {total} cartes pour {player_count} joueurs. "
                    f"Retirez {total - player_count - allowed_extra} cartes."
                )
        wolf_count = self.deck.get("Loup-Garou", 0) + \
                     self.deck.get("Grand Méchant Loup", 0) + \
                     self.deck.get("Village Infect", 0)
        if wolf_count == 0:
            errors.append("Il doit y avoir au moins 1 Loup-Garou.")
        return errors

    def to_dict(self) -> dict:
        return {
            "enabled_extensions":     list(self.enabled_extensions),
            "deck":                   self.deck,
            "debate_duration":        self.debate_duration,
            "night_role_timeout":     self.night_role_timeout,
            "wolves_timeout":         self.wolves_timeout,
            "vote_timeout":           self.vote_timeout,
            "first_night_only_thief": self.first_night_only_thief,
            "first_night_only_cupid": self.first_night_only_cupid,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameConfig":
        obj = cls(
            enabled_extensions=set(data.get("enabled_extensions", ["base"])),
            deck=data.get("deck", {}),
            debate_duration=data.get("debate_duration", C.PHASE_TIMEOUT_DAY_DEBATE),
            night_role_timeout=data.get("night_role_timeout", C.PHASE_TIMEOUT_NIGHT_ROLE),
            wolves_timeout=data.get("wolves_timeout", C.PHASE_TIMEOUT_WOLVES),
            vote_timeout=data.get("vote_timeout", C.PHASE_TIMEOUT_DAY_VOTE),
            first_night_only_thief=data.get("first_night_only_thief", True),
            first_night_only_cupid=data.get("first_night_only_cupid", True),
        )
        return obj
