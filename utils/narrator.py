"""
utils/narrator.py — Messages de narration d'ambiance.
Textes envoyés dans les salons privés et le village pour créer l'immersion.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import discord

import config as C

if TYPE_CHECKING:
    from core.game import Game

log = logging.getLogger(__name__)


# ─── Textes de narration par rôle ────────────────────────────────────────────

ROLE_NARRATION: dict[str, dict] = {
    "Voleur": {
        "wake": "🃏 *Dans le silence de la nuit, une ombre se faufile...*\n**Le Voleur se réveille et peut choisir son destin.**",
        "sleep": "🃏 *Le Voleur s'endort, son choix fait.*",
        "public": "🃏 *Le Voleur décide de son identité dans l'obscurité...*",
    },
    "Cupidon": {
        "wake": "❤️ *Cupidon bande son arc et vise les cœurs endormis...*\n**Cupidon, désignez vos amoureux !**",
        "sleep": "❤️ *La flèche d'amour a été décochée. Cupidon se rendort.*",
        "public": "❤️ *Cupidon s'envole dans la nuit, arc en main...*",
    },
    "Les Deux Sœurs": {
        "wake": "👧 *Deux silhouettes s'éveillent doucement...*\n**Les Sœurs se reconnaissent dans l'obscurité.**",
        "sleep": "👧 *Les Sœurs échangent un regard complice avant de se rendormir.*",
        "public": "👧 *Deux âmes sœurs partagent un secret dans la nuit...*",
    },
    "Les Trois Frères": {
        "wake": "👦 *Trois ombres se lèvent en silence...*\n**Les Frères s'identifient l'un l'autre.**",
        "sleep": "👦 *Les Frères se rendorment, soudés pour toujours.*",
        "public": "👦 *Trois frères se retrouvent dans les ténèbres...*",
    },
    "Voyante": {
        "wake": "👁️ *La brume du sommeil se dissipe...*\n**La Voyante ouvre les yeux et scrute les âmes.**",
        "sleep": "👁️ *La Voyante referme ses yeux, emportant ses visions.*",
        "public": "👁️ *Une présence mystérieuse observe le village dans le noir...*",
    },
    "Renard": {
        "wake": "🦊 *Le Renard pointe son museau fuselé...*\n**Le Renard renifle les odeurs suspectes.**",
        "sleep": "🦊 *Le Renard se tait et se rendort.*",
        "public": "🦊 *Une forme silencieuse flairer le vent nocturne...*",
    },
    "Joueur de Flûte": {
        "wake": "🪗 *Une mélodie envoûtante s'élève dans la nuit...*\n**Le Joueur de Flûte charme ses victimes.**",
        "sleep": "🪗 *La musique s'évanouit dans la brume.*",
        "public": "🪗 *Une musique étrange envahit le village endormi...*",
    },
    "Loup-Garou": {
        "wake": "🐺 *Des yeux jaunes s'ouvrent dans les ténèbres...*\n**Les Loups-Garous se réveillent et désignent leur victime !**",
        "sleep": "🐺 *Les hurlements s'estompent. Les loups se fondent dans la nuit.*",
        "public": "🐺 *Des hurlements déchirent le silence... Les loups rôdent !*",
    },
    "Sorcière": {
        "wake": "🧪 *L'odeur de vieilles herbes et de soufre s'infiltre...*\n**La Sorcière consulte ses mystérieux breuvages.**",
        "sleep": "🧪 *La Sorcière range ses potions et se rendort.*",
        "public": "🧪 *Une fumée étrange s'échappe d'une maisonnette...*",
    },
    "Salvateur": {
        "wake": "🛡️ *Une silhouette veillante se lève dans l'ombre...*\n**Le Salvateur choisit qui protéger cette nuit.**",
        "sleep": "🛡️ *Le Salvateur reprend son poste de veille.*",
        "public": "🛡️ *Un gardien silencieux veille sur le village...*",
    },
}

NIGHT_OPENING = (
    "🌙 **La nuit tombe sur le village de Thiercelieux...**\n\n"
    "*Les habitants ferment leurs volets, éteignent leurs bougies.*\n"
    "*Un silence inquiet s'installe. Quelque chose rôde dans l'obscurité...*"
)

NIGHT_CLOSING = (
    "🌅 **L'aube se lève lentement...**\n\n"
    "*Les coqs chantent. Les habitants rouvrent leurs yeux, anxieux.*\n"
    "*La nuit a-t-elle épargné le village ?*"
)


class Narrator:
    """Gère l'envoi des messages de narration dans les salons."""

    def __init__(self, game: "Game"):
        self.game = game

    async def announce_night_start(self) -> None:
        """Annonce le début de la nuit dans le salon du village."""
        if not self.game.village_text:
            return
        embed = discord.Embed(
            title="🌙 La nuit tombe…",
            description=NIGHT_OPENING,
            color=C.COLOR_NIGHT,
        )
        embed.set_footer(text="Tous les joueurs rejoignent leur maison…")
        await self.game.village_text.send(embed=embed)

    async def announce_night_role(self, role_name: str) -> None:
        """
        Envoie un message d'ambiance public dans le village pour chaque rôle
        qui se réveille, sans révéler qui joue ce rôle.
        """
        if not self.game.village_text:
            return
        narration = ROLE_NARRATION.get(role_name, {})
        public_msg = narration.get("public", f"*Quelqu'un s'éveille dans la nuit…*")
        await self.game.village_text.send(public_msg)
        await asyncio.sleep(1)  # Petite pause pour le rythme

    async def send_role_wake(self, role_name: str, channel: discord.TextChannel) -> None:
        """Envoie le message de réveil dans le salon privé du joueur."""
        narration = ROLE_NARRATION.get(role_name, {})
        msg = narration.get("wake", f"*C'est votre tour d'agir…*")
        await channel.send(msg)

    async def send_role_sleep(self, role_name: str, channel: discord.TextChannel) -> None:
        """Envoie le message de sommeil dans le salon privé du joueur."""
        narration = ROLE_NARRATION.get(role_name, {})
        msg = narration.get("sleep", f"*Vous vous rendormez…*")
        await channel.send(msg)

    async def announce_day_start(self, deaths: list) -> None:
        """Annonce le début de la journée avec les morts de la nuit."""
        if not self.game.village_text:
            return

        embed = discord.Embed(
            title="☀️ L'aube se lève sur Thiercelieux…",
            color=C.COLOR_DAY,
        )

        if not deaths:
            embed.description = (
                "🌟 *Miracle ! Le village se réveille intact.*\n"
                "*Personne n'est mort cette nuit.*"
            )
        else:
            death_list = "\n".join(
                f"💀 **{p.display_name}** ({p.role.name if p.role else '???'})"
                for p in deaths
            )
            embed.description = (
                f"*Le village se réveille, hanté par les événements de la nuit…*\n\n"
                f"**Victimes de la nuit :**\n{death_list}"
            )
        await self.game.village_text.send(embed=embed)

    async def announce_execution(self, victim) -> None:
        """Annonce l'exécution d'un joueur au bûcher."""
        if not self.game.village_text:
            return
        embed = discord.Embed(
            title="🔥 Le village a parlé !",
            description=(
                f"**{victim.display_name}** est conduit·e au bûcher.\n"
                f"*Ses dernières paroles résonnent dans le silence…*\n\n"
                f"Son rôle était : **{victim.role.name if victim.role else '???'}**"
            ),
            color=C.COLOR_DEATH,
        )
        await self.game.village_text.send(embed=embed)

    async def announce_victory(self, team: str) -> None:
        """Annonce la fin de la partie et l'équipe gagnante."""
        if not self.game.village_text:
            return

        messages = {
            "village": (
                "☀️ **Victoire du Village !**",
                "Les Loups-Garous ont été éliminés. La paix revient à Thiercelieux !\n"
                "*Les villageois peuvent enfin dormir tranquilles…*",
                C.COLOR_DAY,
            ),
            "loups": (
                "🐺 **Victoire des Loups-Garous !**",
                "Les loups ont dévoré suffisamment de victimes pour contrôler le village.\n"
                "*L'obscurité règne sur Thiercelieux pour toujours…*",
                C.COLOR_WOLVES,
            ),
            "joueur_de_flute": (
                "🪗 **Victoire du Joueur de Flûte !**",
                "Tous les villageois sont tombés sous l'emprise de sa mélodie envoûtante.\n"
                "*La musique résonne, hypnotique, pour l'éternité…*",
                C.COLOR_NIGHT,
            ),
            "ange": (
                "😇 **L'Ange a gagné !**",
                "L'Ange a accompli sa mission mystérieuse et quitte ce monde avec grâce.",
                0xffd700,
            ),
        }

        title, desc, color = messages.get(
            team,
            ("🏆 Fin de partie !", "La partie est terminée.", C.COLOR_INFO)
        )
        embed = discord.Embed(title=title, description=desc, color=color)
        await self.game.village_text.send(embed=embed)
