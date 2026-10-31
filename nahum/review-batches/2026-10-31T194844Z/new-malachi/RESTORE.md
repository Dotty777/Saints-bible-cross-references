# Malachi recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Preserve every completed object, source field, ordered unit, reference, anchor and prior review batch. Recover the exact source commit and blob in source-checks.json. Never bootstrap over existing records. Read-but-deferred units retain zero credit. Run python scripts/render_genesis.py and python scripts/validate.py --write-verification after changes.
