"""
utils/vote_manager.py — Gestion du système de vote interactif (Discord UI).
Utilisé pour le vote du bûcher (jour) et le vote des loups (nuit).
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Optional, TYPE_CHECKING

import discord

import config as C

if TYPE_CHECKING:
    from core.game import Game
    from core.player import Player

log = logging.getLogger(__name__)


class VoteSession:
    """
    Session de vote générique (majorité simple).
    Gère les votes par boutons Discord dans un salon donné.
    """

    def __init__(
        self,
        game: "Game",
        channel: discord.TextChannel,
        voters: list["Player"],
        candidates: list["Player"],
        title: str,
        timeout: int,
        anonymous: bool = False,
    ):
        self.game       = game
        self.channel    = channel
        self.voters     = voters
        self.candidates = candidates
        self.title      = title
        self.timeout    = timeout
        self.anonymous  = anonymous

        self._votes: dict[int, int] = {}   # voter_id → candidate_id
        self._done  = asyncio.Event()
        self._msg:  Optional[discord.Message] = None

    async def run(self) -> Optional["Player"]:
        """
        Lance la session de vote et attend le résultat.
        Retourne le joueur éliminé, ou None en cas d'égalité absolue.
        """
        embed, view = self._build_vote_embed()
        self._msg = await self.channel.send(embed=embed, view=view)

        # Lance un countdown
        countdown_task = asyncio.create_task(self._countdown())

        try:
            await asyncio.wait_for(self._done.wait(), timeout=self.timeout)
        except asyncio.TimeoutError:
            pass
        finally:
            countdown_task.cancel()
            view.stop()

        return self._tally()

    def _build_vote_embed(self) -> tuple[discord.Embed, "VoteView"]:
        embed = discord.Embed(
            title=self.title,
            description=(
                f"Cliquez sur le nom du joueur à éliminer.\n"
                f"**Vous avez {self.timeout}s pour voter.**\n"
                f"*(Majorité simple — le plus de voix gagne)*"
            ),
            color=C.COLOR_WOLVES if self.anonymous else C.COLOR_DAY,
        )
        view = VoteView(self)
        return embed, view

    async def _countdown(self) -> None:
        """Met à jour le message de vote avec le temps restant."""
        elapsed = 0
        while elapsed < self.timeout:
            await asyncio.sleep(C.PHASE_COUNTDOWN_INTERVAL)
            elapsed += C.PHASE_COUNTDOWN_INTERVAL
            remaining = self.timeout - elapsed
            if remaining > 0 and self._msg:
                try:
                    embed = self._msg.embeds[0] if self._msg.embeds else None
                    if embed:
                        embed.set_footer(text=f"⏳ Temps restant : {remaining}s")
                        await self._msg.edit(embed=embed)
                except discord.HTTPException:
                    pass

    def record_vote(self, voter_id: int, candidate_id: int) -> None:
        """Enregistre ou modifie le vote d'un joueur."""
        self._votes[voter_id] = candidate_id
        # Si tous les électeurs ont voté, termine immédiatement
        if len(self._votes) >= len(self.voters):
            self._done.set()

    def _tally(self) -> Optional["Player"]:
        """Dépouillement : retourne le gagnant ou None si égalité."""
        if not self._votes:
            return None

        counts = Counter(self._votes.values())
        max_votes = max(counts.values())
        leaders = [cid for cid, cnt in counts.items() if cnt == max_votes]

        if len(leaders) > 1:
            log.info("Égalité au vote (%s votes chacun)", max_votes)
            return None   # Égalité → géré par l'appelant

        winner_id = leaders[0]
        # Retrouve le Player correspondant
        for p in self.candidates:
            if p.id == winner_id:
                return p
        return None

    def build_result_embed(self, victim: Optional["Player"]) -> discord.Embed:
        """Construit l'embed de résultat du vote."""
        counts = Counter(self._votes.values()) if self._votes else Counter()

        lines = []
        for p in self.candidates:
            count = counts.get(p.id, 0)
            bar   = "█" * count + "░" * (len(self.voters) - count)
            lines.append(f"{p.display_name}: {count} vote(s) `{bar}`")

        embed = discord.Embed(
            title="📊 Résultat du vote",
            description="\n".join(lines) or "*Aucun vote*",
            color=C.COLOR_DEATH if victim else C.COLOR_INFO,
        )
        if victim:
            embed.add_field(
                name="☠️ Éliminé",
                value=f"**{victim.display_name}** est conduit·e au bûcher.",
                inline=False,
            )
        else:
            embed.add_field(
                name="⚖️ Égalité",
                value="Personne n'est éliminé (ou le Bouc Émissaire prend la place).",
                inline=False,
            )
        return embed


class VoteView(discord.ui.View):
    """Interface boutons pour voter."""

    def __init__(self, session: VoteSession):
        super().__init__(timeout=None)
        self.session = session

        for candidate in session.candidates:
            btn = discord.ui.Button(
                label=candidate.display_name,
                style=discord.ButtonStyle.primary,
                custom_id=f"vote_{candidate.id}",
            )
            btn.callback = self._make_callback(candidate)
            self.add_item(btn)

    def _make_callback(self, candidate: "Player"):
        async def callback(interaction: discord.Interaction):
            # Vérifie que le votant est autorisé
            voter = self.session.game.get_player(interaction.user)
            if voter is None or voter not in self.session.voters:
                await interaction.response.send_message(
                    "Vous ne pouvez pas voter.", ephemeral=True
                )
                return
            # Vérifie que l'Idiot du Village ou le Bouc Émissaire n'a pas perdu le droit de vote
            if voter.role and hasattr(voter.role, "can_vote") and not voter.role.can_vote:
                await interaction.response.send_message(
                    "Vous n'avez plus le droit de voter.", ephemeral=True
                )
                return

            already = self.session._votes.get(voter.id)
            self.session.record_vote(voter.id, candidate.id)

            if already and already != candidate.id:
                await interaction.response.send_message(
                    f"🔄 Vous avez changé votre vote pour **{candidate.display_name}**.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"✅ Vous avez voté pour **{candidate.display_name}**.",
                    ephemeral=True,
                )
        return callback
