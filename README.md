# mod-tier0-trainers

Remaps classic-continent profession trainers so **Tier 0 / level-60** progression can train professions to skill **300** without relying on TBC/WotLK-only trainer lists.

Designed to work alongside [mod-individual-progression](https://github.com/ZhengPeiRu21/mod-individual-progression) Tier 0.

## Purpose / scope

| Layer | Role |
|-------|------|
| Module SQL | Trainer spell lists / creature trainer bindings for classic continents |
| `Tier0Trainers.Enable` in conf | Documented enable flag (SQL applies when installed) |

Does **not** change profession skill caps in core, recipe discovery, or Outland/Northrend trainer content beyond what the SQL remaps.

## Configuration

See `conf/tier0Trainers.conf.dist`:

| Key | Default | Meaning |
|-----|---------|---------|
| `Tier0Trainers.Enable` | 1 | Documented master switch for operators |

Realm overlays usually leave this at `.dist` (SQL-only policy).

## Install

```bash
cd modules
git submodule add https://github.com/VenomekPL/mod-tier0-trainers.git mod-tier0-trainers
# CMake reconfigure + rebuild; worldserver applies module SQL on start
```

## License

AGPL-3.0
