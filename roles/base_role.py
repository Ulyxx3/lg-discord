"""
roles/base_role.py — Classe abstraite pour tous les rôles du jeu.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player


class BaseRole(ABC):
    """
    Classe de base pour tous les rôles de Loup-Garou.

    Attributs de classe à surcharger :
      name        : Nom affiché du rôle.
      team        : Équipe ("village", "loups", "neutre").
      description : Description courte du rôle.
      emoji       : Emoji représentatif.
      night_order : Priorité d'action nocturne (plus petit = plus tôt).
                    None = pas d'action nocturne.
      extension   : Extension d'origine ("base", "nouvelle_lune", …).
    """

    name:        str = "Rôle inconnu"
    team:        str = "village"
    description: str = "Aucune description."
    emoji:       str = "❓"
    night_order: Optional[int] = None   # None = pas de tour nocturne
    extension:   str = "base"
    # first_night_only : si True, ce rôle n'agit que la 1ère nuit
    first_night_only: bool = False

    async def night_action(self, game: "Game", player: "Player") -> None:
        """
        Logique du tour nocturne de ce rôle.
        Appelé par night_phase.py quand c'est le tour de ce rôle.
        Ne fait rien par défaut (rôles passifs).
        """
        pass

    async def on_death(self, game: "Game", player: "Player") -> None:
        """
        Effet déclenché à la mort du joueur (ex: Chasseur tire, Ancien affaiblit le village).
        Appelé par game.kill_player().
        """
        pass

    async def on_love_death(self, game: "Game", player: "Player") -> None:
        """
        Effet déclenché quand ce joueur meurt par lien amoureux.
        Par défaut : rien.
        """
        pass

    def can_act(self, game: "Game", player: "Player") -> bool:
        """
        Vérifie si le joueur peut agir ce tour-ci.
        Par défaut : joueur vivant ET c'est son tour dans la phase courante.
        """
        return player.is_alive

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} team={self.team}>"
