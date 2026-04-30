"""
core/state_machine.py — Machine à états du jeu.
Définit GamePhase et NightState (contexte d'une nuit).
"""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.player import Player


class GamePhase(Enum):
    """Toutes les phases possibles d'une partie."""
    IDLE        = "idle"         # Aucune partie en cours
    CONFIGURING = "configuring"  # L'admin configure le deck de rôles
    WAITING     = "waiting"      # Inscription des joueurs (/lg join)
    NIGHT_START = "night_start"  # Transition nuit (déplacements vocaux)
    NIGHT_ROLE  = "night_role"   # Tour d'un rôle nocturne (générique)
    DAY_START   = "day_start"    # Transition jour (déplacements vocaux)
    DAY_DEBATE  = "day_debate"   # Débat libre + timer
    DAY_VOTE    = "day_vote"     # Vote du bûcher
    DAY_DEATH   = "day_death"    # Annonce mort + vérification fin
    GAME_OVER   = "game_over"    # Fin de partie


@dataclass
class NightState:
    """
    Contexte d'une nuit : mémorise les décisions prises
    pendant les différents tours nocturnes.
    Réinitialisé à chaque nouvelle nuit.
    """
    wolf_victim:   Optional["Player"] = None   # Cible choisie par les loups
    witch_saved:   bool               = False  # Sorcière a utilisé la potion de vie
    witch_victim:  Optional["Player"] = None   # Cible empoisonnée par la sorcière
    seer_revealed: Optional["Player"] = None   # Joueur regardé par la voyante
    hunter_shot:   Optional["Player"] = None   # Cible abattue par le chasseur
    piper_charmed: list["Player"]     = field(default_factory=list)  # Envoûtés
    protected:     Optional["Player"] = None   # Joueur protégé par le Salvateur
    # Joueurs morts cette nuit (calculé en fin de nuit)
    deaths_tonight: list["Player"]   = field(default_factory=list)
    # Rôle actuellement en train d'agir
    current_role_name: Optional[str] = None

    def reset(self) -> None:
        """Réinitialise l'état de nuit pour un nouveau cycle."""
        self.wolf_victim    = None
        self.witch_saved    = False
        self.witch_victim   = None
        self.seer_revealed  = None
        self.hunter_shot    = None
        self.piper_charmed  = []
        self.protected      = None
        self.deaths_tonight = []
        self.current_role_name = None
