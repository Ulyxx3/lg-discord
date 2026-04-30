# 🐺 lg-discord — Bot Loup-Garou de Thiercelieux

Bot Discord "Maître du Jeu" complet pour le jeu **Loup-Garou de Thiercelieux**.  
Il gère absolument tout : salons, permissions, cycles Jour/Nuit, rôles spéciaux, votes, narration et persistance.

---

## ✨ Fonctionnalités

| Fonctionnalité | Détail |
|---|---|
| **Gestion des salons** | Création dynamique de maisons privées par joueur, salon des loups, catégorie admin |
| **Anonymat garanti** | Permissions Discord (`@everyone=deny`) — personne ne peut voir le salon d'un autre |
| **Cycle Jour/Nuit** | Machine à états avec 10+ phases, déplacements vocaux automatiques |
| **Rate-limit proof** | File d'attente asyncio avec délai entre chaque déplacement (25 joueurs max) |
| **Tous les rôles** | Jeu de base + extension Nouvelle Lune (26 rôles implémentés) |
| **Deck configurable** | Sélection des extensions et quantités par rôle avant la partie |
| **Discord UI** | Boutons interactifs pour chaque action nocturne (pas de commandes texte) |
| **Narration d'ambiance** | Messages synchronisés par rôle dans les salons privés et le village |
| **Vote interactif** | Votes par boutons avec countdown en temps réel |
| **Persistance SQLite** | Reprise de partie possible après crash/redémarrage du bot |

---

## 🎭 Rôles implémentés

### Jeu de base
| Rôle | Équipe | Action |
|---|---|---|
| Villageois | 🏘️ Village | — (passif) |
| Loup-Garou | ⚔️ Loups | Vote collectif nocturne |
| Voyante | 🏘️ Village | Révèle le camp d'un joueur |
| Sorcière | 🏘️ Village | 2 potions à usage unique (vie/mort) |
| Chasseur | 🏘️ Village | Tire sur un joueur à sa mort |
| Cupidon | 🏘️ Village | Lie deux amoureux (1ère nuit) |
| Voleur | 🏘️ Village | Échange son rôle (1ère nuit, 2 cartes réservées) |

### Extension Nouvelle Lune
| Rôle | Équipe | Action |
|---|---|---|
| Salvateur | 🏘️ Village | Protège un joueur chaque nuit |
| Ancien | 🏘️ Village | Résiste à la 1ère attaque des loups |
| Bouc Émissaire | 🏘️ Village | Meurt en cas d'égalité, choisit qui peut voter |
| Idiot du Village | 🏘️ Village | Survit au 1er bûcher (perd le droit de vote) |
| Les Deux Sœurs | 🏘️ Village | Se reconnaissent la 1ère nuit |
| Les Trois Frères | 🏘️ Village | Se reconnaissent la 1ère nuit |
| Renard | 🏘️ Village | Renifle 3 joueurs — perd son pouvoir si aucun loup |
| Montreur d'Ours | 🏘️ Village | L'ours grogne si un voisin est loup |
| Juge Bègue | 🏘️ Village | Déclenche un 2ème vote (usage unique) |
| Servante Rusée | 🏘️ Village | Prend le rôle d'un joueur exécuté |
| Petite Fille | 🏘️ Village | Espionne le salon des loups |
| Enfant Sauvage | 🏘️ Village | Devient loup si son modèle meurt |
| Chien-Loup | 🎭 Neutre | Choisit son camp (1ère nuit) |
| Grand Méchant Loup | ⚔️ Loups | Tue une 2ème victime tant que des rôles spéciaux vivent |
| Village Infect | ⚔️ Loups | Convertit la victime en loup (usage unique) |
| Ange | 🎭 Neutre | Gagne solo s'il est exécuté au 1er vote |
| Joueur de Flûte | 🎭 Neutre | Envoûte 2 joueurs/nuit — gagne si tous envoûtés |
| Acteur | 🏘️ Village | Joue 3× un rôle tiré au sort |

---

## 🚀 Installation

### 1. Prérequis
- Python 3.11+
- Un bot Discord avec les **Intents privileged** activés : `Server Members` et `Message Content`
- Permissions du bot : **Administrateur** (ou au minimum : Gérer les salons, Gérer les rôles, Déplacer les membres)

### 2. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 3. Configuration
```bash
cp .env.example .env
# Éditez .env et ajoutez votre DISCORD_TOKEN
```

### 4. Lancement
```bash
python bot.py
```

---

## 🎮 Guide d'utilisation

### Première configuration (admin)
```
/lg setup       → Initialise les salons et rôles Discord du serveur
```

### Avant chaque partie (admin)
```
/lg open        → Ouvre les inscriptions
/lg config      → Configure les extensions et le deck de rôles
/lg deck <rôle> <quantité>  → Ajuste finement le deck
```

### Inscription des joueurs
```
/lg join        → Rejoindre la partie
/lg leave       → Quitter (avant le début)
/lg players     → Voir la liste des joueurs
```

### Lancement (admin)
```
/lg start       → Lance la partie (distribue les rôles, démarre la 1ère nuit)
```

### Pendant la partie
```
/lg role        → Rappel de votre rôle secret (ephemeral)
/lg status      → État de la partie
/lg revote      → [Juge Bègue] Demande un 2ème vote
/lg stop        → [Admin] Arrêt d'urgence
/lg kick @user  → [Admin] Exclure un joueur
```

---

## 🏗️ Architecture

```
lg-discord/
├── bot.py                  # Point d'entrée
├── config.py               # Constantes globales
├── core/                   # Logique centrale (Game, StateMachine, ChannelManager, Persistence)
├── roles/                  # 26 rôles + registre
├── phases/                 # 4 phases (setup, night, day, vote)
├── commands/               # 3 cogs de commandes slash
└── utils/                  # MoveQueue, Narrator, VoteManager, EmbedBuilder
```

---

## ⚙️ Configuration avancée

Tous les timers et constantes sont dans `config.py` :

| Constante | Défaut | Description |
|---|---|---|
| `PHASE_TIMEOUT_NIGHT_ROLE` | 90s | Temps max par rôle nocturne |
| `PHASE_TIMEOUT_WOLVES` | 120s | Temps max pour le vote des loups |
| `PHASE_TIMEOUT_DAY_DEBATE` | 300s | Durée du débat de jour |
| `PHASE_TIMEOUT_DAY_VOTE` | 120s | Temps max pour le vote du bûcher |
| `MOVE_DELAY_SECONDS` | 0.6s | Délai entre chaque déplacement vocal |
| `MAX_PLAYERS` | 25 | Limite de joueurs par partie |

---

## 📄 Licence

MIT — voir [LICENSE](LICENSE)