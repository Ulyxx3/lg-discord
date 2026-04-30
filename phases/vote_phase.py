"""
phases/vote_phase.py — Vote public du bûcher + gestion des cas spéciaux.
Gère : vote ordinaire, Idiot du Village, Bouc Émissaire (égalité),
Servante Rusée, Ange (1er tour), Juge Bègue (2ème vote).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

from core.state_machine import GamePhase
from utils.narrator import Narrator
from utils.vote_manager import VoteSession

import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class VotePhase:
    """Gère le vote du bûcher et tous ses cas particuliers."""

    def __init__(self, game: "Game"):
        self.game     = game
        self.narrator = Narrator(game)

    async def run(self) -> Optional["Player"]:
        """
        Lance le vote du bûcher.
        Retourne le joueur éliminé, ou None si la partie continue sans mort.
        """
        game = self.game
        game.phase = GamePhase.DAY_VOTE
        await game.save()

        victim = await self._run_vote_round()

        # ── Cas spéciaux post-vote ──────────────────────────────────────────

        # Égalité → Bouc Émissaire prend la place
        if victim is None:
            victim = await self._handle_tie()

        # Idiot du Village : survit au premier bûcher
        if victim and victim.role and victim.role.name == "Idiot du Village":
            if not victim.role.revealed:   # type: ignore[attr-defined]
                await self._handle_idiot(victim)
                return None  # Personne n'est éliminé

        # Ange : victoire solo s'il est éliminé au 1er vote
        if victim and victim.role and victim.role.name == "Ange":
            if not victim.role.first_vote_passed:  # type: ignore[attr-defined]
                await self.narrator.announce_victory("ange")
                await game.kill_player(victim, reason="bûcher")
                game.phase = GamePhase.GAME_OVER
                return victim

        # Vote ordinaire
        if victim:
            game.phase = GamePhase.DAY_DEATH
            await self.narrator.announce_execution(victim)
            await game.kill_player(victim, reason="bûcher")

            # Servante Rusée : offre de prendre le rôle
            await self._offer_rust_maid(victim)

            # Chasseur : déclenche son tir si mort au bûcher
            if victim.role and victim.role.name == "Chasseur":
                await victim.role.on_death(game, victim)

        # ── Juge Bègue : 2ème vote possible ─────────────────────────────────
        judge = self._find_player_with_role("Juge Bègue")
        if (
            judge and judge.is_alive
            and judge.role.wants_revote   # type: ignore[attr-defined]
            and judge.role.has_used_power  # type: ignore[attr-defined]
        ):
            judge.role.wants_revote = False  # type: ignore[attr-defined]
            if game.village_text:
                await game.village_text.send(
                    "⚖️ *Le Juge Bègue demande un second vote !*"
                )
            second_victim = await self._run_vote_round()
            if second_victim:
                await self.narrator.announce_execution(second_victim)
                await game.kill_player(second_victim, reason="bûcher_second")

        # Marque l'Ange si le premier vote est passé
        angel = self._find_player_with_role("Ange")
        if angel and angel.is_alive and angel.role:
            if not angel.role.first_vote_passed:   # type: ignore[attr-defined]
                angel.role.fail_angel_objective()  # type: ignore[attr-defined]

        await game.save()
        return victim

    # ─────────────────────────────────────────────────────────────────────────

    async def _run_vote_round(self) -> Optional["Player"]:
        """Lance un round de vote et retourne la victime (ou None si égalité)."""
        game       = self.game
        alive      = game.alive_players
        candidates = [p for p in alive if not (
            p.role and hasattr(p.role, "revealed") and p.role.revealed
        )]  # L'Idiot révélé n'est plus candidat

        if not candidates:
            return None

        # Électeurs : joueurs vivants avec droit de vote
        voters = [
            p for p in alive
            if not (p.role and hasattr(p.role, "can_vote") and not p.role.can_vote)
        ]

        # Bouc Émissaire : whitelist éventuelle
        scapegoat = self._find_player_with_role("Bouc Émissaire")
        if (
            scapegoat and not scapegoat.is_alive
            and scapegoat.role
            and scapegoat.role.vote_whitelist  # type: ignore[attr-defined]
        ):
            whitelist_ids = set(scapegoat.role.vote_whitelist)
            voters = [v for v in voters if v.id in whitelist_ids]

        session = VoteSession(
            game       = game,
            channel    = game.village_text,
            voters     = voters,
            candidates = candidates,
            title      = "🗳️ Vote du Bûcher",
            timeout    = game.game_config.vote_timeout,
        )
        victim = await session.run()

        result_embed = session.build_result_embed(victim)
        if game.village_text:
            await game.village_text.send(embed=result_embed)

        return victim

    async def _handle_tie(self) -> Optional["Player"]:
        """En cas d'égalité : le Bouc Émissaire est éliminé s'il est en vie."""
        game = self.game
        scapegoat_player = self._find_player_with_role("Bouc Émissaire")

        if scapegoat_player and scapegoat_player.is_alive:
            if game.village_text:
                import discord
                await game.village_text.send(
                    embed=discord.Embed(
                        title="🐐 Égalité ! Le Bouc Émissaire est désigné !",
                        description=(
                            f"**{scapegoat_player.display_name}** (Bouc Émissaire) "
                            "est éliminé·e à cause de l'égalité des votes."
                        ),
                        color=C.COLOR_DEATH,
                    )
                )
            await scapegoat_player.role.on_death(game, scapegoat_player)
            await game.kill_player(scapegoat_player, reason="bûcher_égalité")
            return scapegoat_player

        # Pas de Bouc Émissaire → personne n'est éliminé
        if game.village_text:
            import discord
            await game.village_text.send(
                embed=discord.Embed(
                    title="⚖️ Égalité !",
                    description="Personne n'est éliminé aujourd'hui.",
                    color=C.COLOR_INFO,
                )
            )
        return None

    async def _handle_idiot(self, player: "Player") -> None:
        """L'Idiot du Village survit à son premier bûcher."""
        player.role.survive_vote()  # type: ignore[attr-defined]
        if self.game.village_text:
            import discord
            await self.game.village_text.send(
                embed=discord.Embed(
                    title="🤡 L'Idiot du Village se révèle !",
                    description=(
                        f"**{player.display_name}** est l'Idiot du Village !\n"
                        "Le village, pris de pitié, le laisse vivre…\n"
                        "*(Il ne peut plus voter désormais)*"
                    ),
                    color=C.COLOR_INFO,
                )
            )

    async def _offer_rust_maid(self, victim: "Player") -> None:
        """Propose à la Servante Rusée de prendre le rôle de la victime."""
        rust_maid_player = self._find_player_with_role("Servante Rusée")
        if rust_maid_player and rust_maid_player.is_alive and rust_maid_player.role:
            if not rust_maid_player.role.has_used:  # type: ignore[attr-defined]
                await rust_maid_player.role.offer_role_swap(  # type: ignore[attr-defined]
                    self.game, rust_maid_player, victim
                )

    def _find_player_with_role(self, role_name: str) -> Optional["Player"]:
        for p in self.game.players.values():
            if p.role and p.role.name == role_name:
                return p
        return None
