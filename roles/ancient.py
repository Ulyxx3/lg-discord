"""
roles/ancient.py — L'Ancien.
Il résiste à la première attaque des loups.
S'il est tué par le village (bûcher), tous les villageois perdent leurs pouvoirs spéciaux.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from roles.base_role import BaseRole

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class Ancient(BaseRole):
    name        = "Ancien"
    team        = "village"
    description = "Résiste à la 1ère attaque des loups. Si tué par le village : les rôles spéciaux perdent leurs pouvoirs."
    emoji       = "🪶"
    night_order = None
    extension   = "nouvelle_lune"

    def __init__(self):
        self._survived_wolves = False  # A-t-il déjà survécu aux loups ?
        self._powers_lost     = False

    async def on_death(self, game: "Game", player: "Player") -> None:
        """Si l'Ancien est tué par le village, désactive les pouvoirs des rôles village."""
        # Vérifie si la mort vient du bûcher (game.night_state.deaths_tonight est vide → mort de jour)
        # Convention : si deaths_tonight ne contient pas player, c'est un mort de jour
        is_daytime_kill = player not in game.night_state.deaths_tonight
        if is_daytime_kill and not self._powers_lost:
            self._powers_lost = True
            await self._strip_village_powers(game)
            if game.village_text:
                import discord, config as C
                await game.village_text.send(
                    embed=discord.Embed(
                        title="🪶 La colère de l'Ancien…",
                        description=(
                            "En mourant sur le bûcher, l'Ancien a maudit le village.\n"
                            "**Tous les rôles spéciaux du village ont perdu leurs pouvoirs !**"
                        ),
                        color=C.COLOR_DEATH,
                    )
                )

    async def _strip_village_powers(self, game: "Game") -> None:
        """Retire les pouvoirs actifs des rôles village (sauf loups)."""
        POWERS_TO_STRIP = {"Voyante", "Sorcière", "Chasseur", "Salvateur", "Renard",
                           "Idiot du Village", "Petite Fille"}
        for p in game.alive_players:
            if p.role and p.role.name in POWERS_TO_STRIP and p.role.team == "village":
                p.role.night_order = None  # Désactive leur tour nocturne
                log.info("Pouvoir retiré à %s (%s)", p.display_name, p.role.name)

    def try_survive_wolves(self) -> bool:
        """
        Appelé par night_phase quand les loups ciblent l'Ancien.
        Retourne True si l'Ancien survit (1ère fois), False sinon.
        """
        if not self._survived_wolves:
            self._survived_wolves = True
            log.info("L'Ancien survit à la première attaque des loups.")
            return True
        return False
