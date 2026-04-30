"""
roles/registry.py — Registre central de tous les rôles disponibles.
Mappe le nom du rôle (str) → la classe Python correspondante.
"""

from __future__ import annotations

from typing import Type

from roles.base_role import BaseRole

# ── Jeu de base ───────────────────────────────────────────────────────────────
from roles.villager          import Villager
from roles.werewolf          import Werewolf
from roles.seer              import Seer
from roles.witch             import Witch
from roles.hunter            import Hunter
from roles.cupid             import Cupid
from roles.thief             import Thief

# ── Extension : Nouvelle Lune ─────────────────────────────────────────────────
from roles.protector         import Protector
from roles.ancient           import Ancient
from roles.scapegoat         import Scapegoat
from roles.idiot             import Idiot
from roles.sisters           import Sisters
from roles.brothers          import Brothers
from roles.fox               import Fox
from roles.bear_tamer        import BearTamer
from roles.stuttering_judge  import StutteringJudge
from roles.rust_maid         import RustMaid
from roles.wild_child        import WildChild
from roles.dog_wolf          import DogWolf
from roles.big_bad_wolf      import BigBadWolf
from roles.vile_father       import VileFather
from roles.little_girl       import LittleGirl
from roles.angel             import Angel
from roles.piper             import Piper
from roles.actor             import Actor


ROLE_REGISTRY: dict[str, Type[BaseRole]] = {
    # Jeu de base
    "Villageois":          Villager,
    "Loup-Garou":          Werewolf,
    "Voyante":             Seer,
    "Sorcière":            Witch,
    "Chasseur":            Hunter,
    "Cupidon":             Cupid,
    "Voleur":              Thief,
    # Nouvelle Lune
    "Salvateur":           Protector,
    "Ancien":              Ancient,
    "Bouc Émissaire":      Scapegoat,
    "Idiot du Village":    Idiot,
    "Les Deux Sœurs":      Sisters,
    "Les Trois Frères":    Brothers,
    "Renard":              Fox,
    "Montreur d'Ours":     BearTamer,
    "Juge Bègue":          StutteringJudge,
    "Servante Rusée":      RustMaid,
    "Enfant Sauvage":      WildChild,
    "Chien-Loup":          DogWolf,
    "Grand Méchant Loup":  BigBadWolf,
    "Village Infect":      VileFather,
    "Petite Fille":        LittleGirl,
    "Ange":                Angel,
    "Joueur de Flûte":     Piper,
    "Acteur":              Actor,
}
