"""验证：alembic upgrade head 与 create_all 的产物结构等价（表/列/主键/外键/索引）。

用法：python scripts/verify_migration.py <migrated.db> <create_all.db>
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sqlalchemy.ext.asyncio import create_async_engine


async def schema_fingerprint(url: str) -> dict:
    eng = create_async_engine(url)
    async with eng.connect() as conn:
        def _inspect(conn_sync):
            from sqlalchemy import inspect
            insp = inspect(conn_sync)
            fp: dict = {}
            for t in sorted(insp.get_table_names()):
                cols = sorted(
                    (c["name"], str(c["type"]).lower(), c["nullable"]) for c in insp.get_columns(t)
                )
                pk = sorted(insp.get_pk_constraint(t)["constrained_columns"])
                fks = sorted(
                    (fk["constrained_columns"][0], fk["referred_table"], tuple(sorted(fk["referred_columns"])))
                    for fk in insp.get_foreign_keys(t)
                )
                idx = sorted((i["name"], tuple(sorted(i["column_names"]))) for i in insp.get_indexes(t))
                fp[t] = {"cols": cols, "pk": pk, "fks": fks, "idx": idx}
            return fp

        fp = await conn.run_sync(_inspect)
    await eng.dispose()
    return fp


async def main() -> None:
    mig_fp = await schema_fingerprint(f"sqlite+aiosqlite:///{sys.argv[1]}")
    create_fp = await schema_fingerprint(f"sqlite+aiosqlite:///{sys.argv[2]}")
    mig_fp.pop("alembic_version", None)

    ok = True
    for name in sorted(set(mig_fp) | set(create_fp)):
        a, b = mig_fp.get(name), create_fp.get(name)
        if a != b:
            ok = False
            print(f"MISMATCH {name}:\n  migrated={a}\n  create_all={b}")
        else:
            print(f"OK {name}: {len(a['cols'])} cols, pk={a['pk']}, fks={len(a['fks'])}, idx={len(a['idx'])}")
    print("\nRESULT:", "IDENTICAL" if ok and mig_fp == create_fp else "DIFFERENT")
    sys.exit(0 if ok and mig_fp == create_fp else 1)


if __name__ == "__main__":
    asyncio.run(main())
