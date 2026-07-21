-- Remove custom capital profession trainer spawns added by 2026_07_11_11.
-- Vanilla creature entries remain; only custom guids are deleted.

DELETE FROM `creature` WHERE `guid` BETWEEN 910020 AND 910024;
