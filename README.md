# mod-tier0-trainers

Remaps classic-continent profession trainers so **Tier 0 / level-60** progression can train professions to skill **300** without relying on TBC/WotLK-only trainer lists.

Designed to work alongside [mod-individual-progression](https://github.com/ZhengPeiRu21/mod-individual-progression) Tier 0.

Fork of [VenomekPL/mod-tier0-trainers](https://github.com/VenomekPL/mod-tier0-trainers).

## What it does

- Creates one tier-0 trainer per profession, **TrainerId 9500900 + n** (blacksmithing 9500902 … fishing 9500915), with recipes and ranks through skill 300. The greeting and locales are copied from the stock trainer.
- Points the classic town/city profession trainers at those lists (`creature_default_trainer`). See [profession-trainers-audit.md](profession-trainers-audit.md) for the NPCs and spells.
- Stock TrainerIds and their `trainer_spell` rows are **not modified**. Outland/Northrend trainers such as K. Lee Smallfry, Dumphry and the Dalaran Grand Masters share those IDs and keep their full lists.
- Trainers whose current list teaches above skill 300 are left alone. That covers the specialization masters (Gnome/Goblin engineers, Dragonscale/Elemental/Tribal leatherworkers) and the Inscription trainers.

The tier-0 lists merge in the ≤300 specialization recipes (Goblin/Gnomish, Dragonscale, ...). They stay gated by the specialization spell through `ReqAbility`.

With mod-individual-progression this replaces its vanilla trainer tiers (town trainers capped at 75/150, capitals at 215/225). Every listed trainer teaches up to 300.

Does **not** change profession skill caps in core, recipe discovery, or Outland/Northrend trainer content.

## Configuration

See `conf/tier0Trainers.conf.dist`:

| Key | Default | Meaning |
|-----|---------|---------|
| `Tier0Trainers.Enable` | 1 | Documented master switch for operators (the SQL applies whenever the module is installed) |

## Install

```bash
cd modules
git clone https://github.com/buildthehomelab/wow-mod-tier0-trainers.git mod-tier0-trainers
# CMake reconfigure + rebuild; worldserver applies data/sql/db-world on start
```

Clone into `mod-tier0-trainers`: AzerothCore derives the loader symbol from the folder name.

## Uninstall

Before remapping, the install SQL saves every NPC's TrainerId in `mod_tier0_trainers_backup`. After removing the module, run [sql/uninstall/mod_tier0_trainers_uninstall.sql](sql/uninstall/mod_tier0_trainers_uninstall.sql) against the world DB. It restores the saved IDs (including other modules' mappings, e.g. mod-individual-progression's) and deletes the tier-0 trainers.

## Regenerating the SQL

```bash
python3 tools/generate-profession-trainer-sql.py --ac-dir /path/to/azerothcore-wotlk
```

`--ac-dir` must be an AzerothCore checkout matching the server. The generator reads `data/sql/base/db_world` from it, then rewrites `data/sql/db-world/`, the uninstall script and the audit.

## License

MIT (see [LICENSE](LICENSE)).
