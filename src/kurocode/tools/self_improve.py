"""
src/kurocode/tools/self_improve.py — Skill Management & Installation Engine.
Supports creating, installing, listing, executing, and removing skills.
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from kurocode.core.paths import SKILLS_DIR


def ensure_skills_dir():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def save_learned_skill(
    name: str,
    description: str,
    steps: Union[str, List[str]],
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Saves a new learned skill as a structured skill directory (skill.json + README.md)
    in the skills directory so Kuro can reuse it.
    """
    ensure_skills_dir()
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower().strip())
    skill_dir = SKILLS_DIR / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    step_list = steps if isinstance(steps, list) else [s.strip() for s in steps.splitlines() if s.strip()]

    manifest = {
        "name": name,
        "slug": slug,
        "description": description,
        "version": "1.0.0",
        "parameters": parameters or {},
        "steps": step_list,
    }

    manifest_file = skill_dir / "skill.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    readme_file = skill_dir / "README.md"
    readme_content = f"# KURO Skill: {name}\n\n**Description:** {description}\n\n### Workflow & Steps:\n"
    readme_content += "\n".join(f"{i}. {s}" for i, s in enumerate(step_list, 1))
    readme_file.write_text(readme_content, encoding="utf-8")

    # Also save flat .md for backwards compatibility
    legacy_file = SKILLS_DIR / f"{slug}.md"
    legacy_file.write_text(readme_content, encoding="utf-8")

    return {
        "success": True,
        "skill_name": name,
        "path": str(skill_dir),
        "message": f"Skill '{name}' registered successfully at {skill_dir}",
    }


def install_skill(source_path: str, skill_name: Optional[str] = None) -> Dict[str, Any]:
    """Installs a skill from an external directory into SKILLS_DIR."""
    ensure_skills_dir()
    src = Path(source_path)
    if not src.exists():
        return {"success": False, "error": f"Source path '{source_path}' does not exist."}

    name = skill_name or src.name
    if src.is_dir() and (src / "skill.json").exists() and not skill_name:
        try:
            m = json.loads((src / "skill.json").read_text(encoding="utf-8"))
            if m.get("name"):
                name = m["name"]
        except Exception:
            pass

    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower().strip())
    target = SKILLS_DIR / slug

    try:
        if src.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                if item.is_dir():
                    shutil.copytree(item, target / item.name, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target / item.name)
        elif src.suffix == ".json":
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target / "skill.json")
        elif src.suffix == ".md":
            target.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target / "README.md")
        return {
            "success": True,
            "skill_name": name,
            "path": str(target),
            "message": f"Skill '{name}' installed successfully.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to install skill: {e}"}


def list_learned_skills() -> List[Dict[str, Any]]:
    """Lists all skills stored in SKILLS_DIR."""
    ensure_skills_dir()
    skills = []
    seen = set()

    # 1. Directory-based skills
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir():
            manifest_file = d / "skill.json"
            if manifest_file.exists():
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    skills.append({
                        "name": data.get("name", d.name),
                        "slug": d.name,
                        "description": data.get("description", ""),
                        "steps_count": len(data.get("steps", [])),
                        "path": str(d),
                    })
                    seen.add(d.name)
                except Exception:
                    pass

    # 2. Legacy .md skills
    for f in sorted(SKILLS_DIR.glob("*.md")):
        if f.stem not in seen:
            try:
                txt = f.read_text(encoding="utf-8")
                skills.append({
                    "name": f.stem,
                    "slug": f.stem,
                    "description": txt[:120].strip(),
                    "steps_count": 1,
                    "path": str(f),
                })
            except Exception:
                pass

    return skills


def delete_skill(name: str) -> bool:
    """Removes a skill from SKILLS_DIR."""
    ensure_skills_dir()
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', name.lower().strip())
    skill_dir = SKILLS_DIR / slug
    deleted = False
    if skill_dir.exists() and skill_dir.is_dir():
        shutil.rmtree(skill_dir, ignore_errors=True)
        deleted = True

    # Check for match in manifest of other directories
    for d in list(SKILLS_DIR.iterdir()):
        if d.is_dir():
            mf = d / "skill.json"
            if mf.exists():
                try:
                    data = json.loads(mf.read_text(encoding="utf-8"))
                    if data.get("name") in (name, slug):
                        shutil.rmtree(d, ignore_errors=True)
                        deleted = True
                except Exception:
                    pass

    legacy_file = SKILLS_DIR / f"{slug}.md"
    if legacy_file.exists():
        legacy_file.unlink(missing_ok=True)
        deleted = True
    return deleted


__all__ = [
    "save_learned_skill",
    "install_skill",
    "list_learned_skills",
    "delete_skill",
    "ensure_skills_dir",
]
