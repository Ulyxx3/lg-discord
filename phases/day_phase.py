"""
phases/day_phase.py — Phase de jour : annonces, grognement d'ours, débat, transitions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

from core.state_machine import GamePhase
from utils.narrator import Narrator

import config as C

if TYPE_CHECKING:
    from core.game import Game

log = logging.getLogger(__name__)


class DayPhase:
    """Gère le passage au jour : annonces des morts, débat minuté."""

    def __init__(self, game: "Game"):
        self.game     = game
        self.narrator = Narrator(game)

    async def run(self) -> None:
        """Transition nuit → jour et gestion du débat."""
        game = self.game
        game.phase = GamePhase.DAY_START
        await game.save()

        log.info("=== JOUR %d COMMENCE ===", game.night_count)

        # 1. Transition vocale
        await game.channel_manager.set_village_day_permissions()
        await asyncio.sleep(2)
        await game.channel_manager.move_all_to_village()

        # 2. Annonce des morts de la nuit
        await self.narrator.announce_day_start(game.night_state.deaths_tonight)

        # 3. Retrait des morts des salons
        for dead_player in game.night_state.deaths_tonight:
            await self._handle_dead_player(dead_player)

        # 4. Grognement de l'Ours (si Montreur d'Ours en vie)
        await self._check_bear_growl()

        # 5. Annonce des envoûtés (Joueur de Flûte)
        await self._announce_charmed()

        # 6. Débat minuté
        game.phase = GamePhase.DAY_DEBATE
        await game.save()
        await self._run_debate_timer()

        log.info("=== DÉBAT TERMINÉ ===")

    async def _run_debate_timer(self) -> None:
        """Affiche un timer de débat avec mises à jour périodiques."""
        game     = self.game
        duration = game.game_config.debate_duration
        interval = C.PHASE_COUNTDOWN_INTERVAL

        if not game.village_text:
            await asyncio.sleep(duration)
            return

        timer_embed = discord.Embed(
            title="☀️ Débat du village",
            description=(
                "Villageois, débattez !\n"
                "Qui est le Loup-Garou parmi vous ?\n\n"
                f"⏳ Temps de débat : **{duration // 60}min {duration % 60}s**"
            ),
            color=C.COLOR_DAY,
        )
        timer_msg = await game.village_text.send(embed=timer_embed)

        elapsed = 0
        while elapsed < duration:
            await asyncio.sleep(interval)
            elapsed += interval
            remaining = duration - elapsed
            if remaining > 0:
                try:
                    timer_embed.set_footer(
                        text=f"⏳ Temps restant : {remaining // 60}min {remaining % 60}s"
                    )
                    await timer_msg.edit(embed=timer_embed)
                except discord.HTTPException:
                    pass

        # Annonce la fin du débat
        if game.village_text:
            await game.village_text.send(
                embed=discord.Embed(
                    title="🗳️ Le temps est venu de voter !",
                    description=(
                        "Le débat est terminé.\n"
                        "**Votez pour désigner le suspect à éliminer au bûcher.**"
                    ),
                    color=C.COLOR_FIRE if hasattr(C, "COLOR_FIRE") else C.COLOR_DAY,
                )
            )

    async def _handle_dead_player(self, player) -> None:
        """Gère les conséquences Discord de la mort d'un joueur pendant le jour."""
        try:
            # Déplace hors du vocal si encore connecté
            if player.member.voice:
                await player.member.move_to(None)
            # Retire l'accès aux salons de joueur actif
            if player.private_text:
                await player.private_text.set_permissions(
                    player.member, view_channel=False
                )
        except discord.HTTPException as e:
            log.warning("Erreur handle_dead_player(%s) : %s", player.display_name, e)

    async def _check_bear_growl(self) -> None:
        """
        Montreur d'Ours : vérifie si ses voisins contiennent un loup.
        Annonce dans le village si c'est le cas.
        """
        game  = self.game
        alive = game.alive_players

        bear_tamer = None
        for p in alive:
            if p.role and p.role.name == "Montreur d'Ours":
                bear_tamer = p
                break

        if not bear_tamer or not game.village_text:
            return

        idx = alive.index(bear_tamer) if bear_tamer in alive else 0
        neighbors = [
            alive[(idx - 1) % len(alive)],
            alive[(idx + 1) % len(alive)],
        ]
        # Retire les doublons si < 3 vivants
        neighbors = [n for n in neighbors if n != bear_tamer]

        has_wolf_neighbor = any(
            n.role and n.role.team == "loups" for n in neighbors
        )

        if has_wolf_neighbor:
            await game.village_text.send(
                embed=discord.Embed(
                    title="🐻 L'Ours grogne !",
                    description=(
                        f"L'ours de **{bear_tamer.display_name}** grogne ce matin !\n"
                        "*Un de ses voisins est peut-être un Loup-Garou…*"
                    ),
                    color=0x8B4513,
                )
            )
        else:
            await game.village_text.send(
                f"🐻 *L'ours de **{bear_tamer.display_name}** est calme ce matin…*"
            )

    async def _announce_charmed(self) -> None:
        """Annonce les nouveaux joueurs envoûtés par le Joueur de Flûte."""
        game        = self.game
        new_charmed = game.night_state.piper_charmed

        if not new_charmed or not game.village_text:
            return

        names = ", ".join(f"**{p.display_name}**" for p in new_charmed)
        await game.village_text.send(
            embed=discord.Embed(
                title="🪗 De nouveaux envoûtés…",
                description=(
                    f"Les joueurs suivants entendent une mélodie étrange dans leur tête :\n"
                    f"{names}\n"
                    "*Ils savent maintenant qu'ils ne sont pas seuls à être envoûtés.*"
                ),
                color=C.COLOR_NIGHT,
            )
        )
        # Les envoûtés se reconnaissent entre eux (message dans leurs salons privés)
        all_charmed = [p for p in game.alive_players if p.is_charmed]
        charmed_names = ", ".join(f"**{p.display_name}**" for p in all_charmed)
        for p in new_charmed:
            if p.private_text:
                await p.private_text.send(
                    f"🪗 *Vous entendez la mélodie du Joueur de Flûte…*\n"
                    f"Vous êtes envoûté·e. Les envoûtés connus : {charmed_names}"
                )
