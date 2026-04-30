"""
phases/night_phase.py — Orchestration complète de la phase de nuit.
Gère la séquence dynamique des tours nocturnes selon les rôles présents.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, TYPE_CHECKING

import discord

from core.state_machine import GamePhase, NightState
from utils.narrator import Narrator
from utils.vote_manager import VoteSession

import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class NightPhase:
    """Gère une nuit complète, de la mise en sommeil du village à l'aube."""

    def __init__(self, game: "Game"):
        self.game     = game
        self.narrator = Narrator(game)

    async def run(self) -> None:
        """Point d'entrée principal de la phase de nuit."""
        game = self.game
        game.night_count += 1
        game.phase = GamePhase.NIGHT_START
        game.night_state.reset()
        await game.save()

        log.info("=== NUIT %d COMMENCE ===", game.night_count)

        # 1. Annonce + transition vocale
        await self.narrator.announce_night_start()
        await game.channel_manager.set_village_night_permissions()
        await asyncio.sleep(2)
        await game.channel_manager.move_all_to_houses()

        # 2. Petite Fille : accès temporaire au salon loups (pendant le tour des loups)
        little_girl = self._find_player_with_role("Petite Fille")

        # 3. Séquence des tours nocturnes (triés par night_order)
        active_roles = self._get_active_night_roles()

        for role_name, players_with_role in active_roles:
            game.phase = GamePhase.NIGHT_ROLE
            game.night_state.current_role_name = role_name
            await game.save()

            log.info("Tour nocturne : %s", role_name)

            # Narration publique dans le village
            await self.narrator.announce_night_role(role_name)

            # Cas spécial : les Loups-Garous ont leur propre logique collective
            if role_name in ("Loup-Garou", "Grand Méchant Loup", "Village Infect", "Chien-Loup"):
                if role_name == "Loup-Garou":
                    # Petite Fille espion
                    if little_girl and little_girl.is_alive:
                        await self._grant_little_girl_spy(little_girl)
                    await self._wolf_collective_vote()
                    if little_girl and little_girl.is_alive:
                        await self._revoke_little_girl_spy(little_girl)
                continue  # Les autres sous-rôles loups agissent séparément

            # Tour individuel pour chaque joueur avec ce rôle
            for player in players_with_role:
                if not player.is_alive:
                    continue

                # Envoie le message de réveil
                if player.private_text:
                    await self.narrator.send_role_wake(role_name, player.private_text)

                # Déclenche l'action nocturne du rôle
                await player.role.night_action(game, player)

                # Message de sommeil
                if player.private_text:
                    await self.narrator.send_role_sleep(role_name, player.private_text)

            # Sous-rôles loups (Grand Méchant Loup, Village Infect) — actions supplémentaires
            if role_name == "Grand Méchant Loup":
                for p in players_with_role:
                    if p.is_alive:
                        await p.role.night_action(game, p)
            elif role_name == "Village Infect":
                for p in players_with_role:
                    if p.is_alive:
                        await p.role.night_action(game, p)

        # 4. Calcul des morts de la nuit
        await self._resolve_night_deaths()

        log.info("=== NUIT %d TERMINÉE ===", game.night_count)

    # ─────────────────────────────────────────────────────────────────────────
    # Vote collectif des Loups
    # ─────────────────────────────────────────────────────────────────────────

    async def _wolf_collective_vote(self) -> None:
        """
        Les loups votent ensemble dans leur salon textuel pour désigner leur victime.
        """
        game     = self.game
        wolves   = game.werewolves   # Loups vivants
        eligible = [p for p in game.alive_players if p.role and p.role.team != "loups"]

        if not eligible or not wolves:
            return

        if not game.wolves_text:
            return

        await game.wolves_text.send(
            embed=discord.Embed(
                title="🐺 Les loups se concertent…",
                description=(
                    "Votez pour désigner votre victime cette nuit.\n"
                    "*(Majorité simple — vous pouvez changer votre vote)*"
                ),
                color=C.COLOR_WOLVES,
            )
        )

        session = VoteSession(
            game       = game,
            channel    = game.wolves_text,
            voters     = wolves,
            candidates = eligible,
            title      = "🐺 Vote des Loups",
            timeout    = game.game_config.wolves_timeout,
            anonymous  = True,
        )
        victim = await session.run()

        # Vérifie si la victime est protégée par le Salvateur
        if victim and game.night_state.protected and victim == game.night_state.protected:
            await game.wolves_text.send(
                "🛡️ *Votre victime est protégée cette nuit… Elle survit !*"
            )
            victim = None

        # Vérifie si la victime est l'Ancien (1ère attaque)
        if victim and victim.role and victim.role.name == "Ancien":
            survived = victim.role.try_survive_wolves()  # type: ignore[attr-defined]
            if survived:
                await game.wolves_text.send(
                    f"🪶 *{victim.display_name} résiste à votre attaque… L'Ancien survit !*"
                )
                victim = None

        game.night_state.wolf_victim = victim

        result_embed = session.build_result_embed(victim)
        await game.wolves_text.send(embed=result_embed)

    # ─────────────────────────────────────────────────────────────────────────
    # Résolution des morts
    # ─────────────────────────────────────────────────────────────────────────

    async def _resolve_night_deaths(self) -> None:
        """Calcule et applique toutes les morts de la nuit."""
        game   = self.game
        deaths: list["Player"] = []

        # Victime des loups
        if game.night_state.wolf_victim:
            deaths.append(game.night_state.wolf_victim)

        # Victime de la Sorcière
        if game.night_state.witch_victim:
            deaths.append(game.night_state.witch_victim)

        # Victime du Grand Méchant Loup (2ème meurtre)
        bbw_victim = getattr(game.night_state, "big_bad_wolf_victim", None)
        if bbw_victim and bbw_victim not in deaths:
            deaths.append(bbw_victim)

        game.night_state.deaths_tonight = deaths

        # Tue tous les joueurs concernés
        for player in deaths:
            await game.kill_player(player, reason="mort_nuit")

        # Chasseur : s'il est mort cette nuit, déclenche son pouvoir
        for player in deaths:
            if player.role and player.role.name == "Chasseur":
                await player.role.on_death(game, player)

        await game.save()

    # ─────────────────────────────────────────────────────────────────────────
    # Séquence dynamique des rôles
    # ─────────────────────────────────────────────────────────────────────────

    def _get_active_night_roles(self) -> list[tuple[str, list["Player"]]]:
        """
        Retourne la liste ordonnée des (nom_rôle, [joueurs]) pour cette nuit.
        - Filtre les rôles first_night_only si ce n'est pas la 1ère nuit.
        - Regroupe les loups sous un seul tour.
        - Trie par night_order.
        """
        from core.game_config import NIGHT_ORDER

        role_players: dict[str, list["Player"]] = {}

        for player in self.game.alive_players:
            if not player.role or player.role.night_order is None:
                continue
            # Filtre first_night_only
            if player.role.first_night_only and self.game.night_count > 1:
                continue

            name = player.role.name
            role_players.setdefault(name, []).append(player)

        # Trie par night_order (NIGHT_ORDER comme référence, fallback sur l'attribut du rôle)
        def sort_key(item: tuple[str, list]) -> int:
            name, players = item
            order = NIGHT_ORDER.get(name)
            if order is not None:
                return order
            return players[0].role.night_order or 99

        sorted_roles = sorted(role_players.items(), key=sort_key)
        return sorted_roles

    def _find_player_with_role(self, role_name: str) -> Optional["Player"]:
        for p in self.game.alive_players:
            if p.role and p.role.name == role_name:
                return p
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Petite Fille — accès espion temporaire
    # ─────────────────────────────────────────────────────────────────────────

    async def _grant_little_girl_spy(self, player: "Player") -> None:
        """Donne temporairement l'accès en lecture au salon des loups."""
        if not self.game.wolves_text:
            return
        try:
            await self.game.wolves_text.set_permissions(
                player.member,
                view_channel=True,
                send_messages=False,
                read_messages=True,
            )
            if player.private_text:
                await player.private_text.send(
                    "👧 *Vous entrouvrez les yeux… Vous pouvez lire le salon des loups !*\n"
                    "*(Attention, si un loup vous y voit, vous mourez à leur place.)*"
                )
        except discord.HTTPException as e:
            log.warning("Petite Fille : erreur permission : %s", e)

    async def _revoke_little_girl_spy(self, player: "Player") -> None:
        """Retire l'accès de la Petite Fille au salon des loups."""
        if not self.game.wolves_text:
            return
        try:
            await self.game.wolves_text.set_permissions(player.member, overwrite=None)
        except discord.HTTPException:
            pass
