"""Re-canonicalize stored skills in ChromaDB after the SkillNormalizer fix.

Usage:
    cd src && python -m scripts.reindex_skills [--dry-run]

What it does (no re-embedding, metadata-only):
- Candidates collection: normalize every chunk's `skills` CSV via
  SkillNormalizer.normalize_skill_list.
- JDs collection: normalize `essential_skills` / `elective_skills` metadata
  + re-enforce elective != essential.

Safe to run multiple times (normalization is idempotent).
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from controllers.VectorDBController import VectorDBController, CANDIDATE_COLLECTION
from controllers.JDController import JD_COLLECTION
from controllers.SkillNormalizer import normalize_skill_list


def _split(csv: str) -> list:
    return [s.strip() for s in (csv or "").split(",") if s.strip()]


def reindex_candidates(dry_run: bool = False) -> dict:
    vdb = VectorDBController()
    coll = vdb._get_collection(CANDIDATE_COLLECTION)
    data = coll.get(include=["metadatas"])
    ids = data.get("ids") or []
    metas = data.get("metadatas") or []
    changed = 0
    for cid, meta in zip(ids, metas):
        meta = meta or {}
        raw = meta.get("skills", "")
        canon = normalize_skill_list(_split(raw))
        canon_csv = ",".join(canon)
        if canon_csv != (raw or ""):
            changed += 1
            if not dry_run:
                coll.update(ids=[cid], metadatas=[{**meta, "skills": canon_csv}])
    return {"chunks": len(ids), "changed": changed}


def reindex_jds(dry_run: bool = False) -> dict:
    vdb = VectorDBController()
    coll = vdb._get_collection(JD_COLLECTION)
    data = coll.get(include=["metadatas"])
    ids = data.get("ids") or []
    metas = data.get("metadatas") or []
    changed = 0
    for jid, meta in zip(ids, metas):
        meta = meta or {}
        ess = normalize_skill_list(_split(meta.get("essential_skills", "")))
        ele = normalize_skill_list(_split(meta.get("elective_skills", "")))
        ess_set = set(ess)
        ele = [s for s in ele if s not in ess_set]
        new_ess_csv, new_ele_csv = ",".join(ess), ",".join(ele)
        if new_ess_csv != (meta.get("essential_skills") or "") or new_ele_csv != (
            meta.get("elective_skills") or ""
        ):
            changed += 1
            if not dry_run:
                coll.update(
                    ids=[jid],
                    metadatas=[
                        {**meta, "essential_skills": new_ess_csv, "elective_skills": new_ele_csv}
                    ],
                )
    return {"jds": len(ids), "changed": changed}


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    print(f"Reindexing skills (dry_run={dry})...")
    c = reindex_candidates(dry_run=dry)
    print(f"Candidates: {c['chunks']} chunks, {c['changed']} normalized.")
    j = reindex_jds(dry_run=dry)
    print(f"JDs: {j['jds']} docs, {j['changed']} normalized.")
    print("Done.")
