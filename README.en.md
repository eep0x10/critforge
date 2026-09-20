<div align="center">

<img src="docs/assets/critforge-banner.png" alt="CritForge — reviewed tabletop miniatures" width="100%">

# CritForge

### From character to reviewed STL.

An agent skill for RPG and board game miniatures with approved references, Meshy 4K geometry, real mesh review, and verified scale.

[![Validation](https://github.com/eep0x10/critforge/actions/workflows/validate.yml/badge.svg)](https://github.com/eep0x10/critforge/actions/workflows/validate.yml)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)](requirements-mesh.txt)
[![MIT license](https://img.shields.io/badge/license-MIT-C89B57?style=flat-square)](LICENSE)

[Get started](#get-started) · [Workflow](#workflow) · [Português](README.md)

</div>

> CritForge finishes at a **corrected, scaled, reviewed STL**. Orientation, hollowing, supports, and slicing stay in your slicer.

## Workflow

```mermaid
flowchart LR
    A[Brief] --> B[Front / rear / face]
    B --> C{Approval}
    C -->|Revise| B
    C -->|Approve| D[Meshy 4K]
    D --> E[Render actual STL]
    E --> F{Bug or mismatch?}
    F -->|Yes| D
    F -->|No| G[Repair and scale]
    G --> H[STL ≤ 45 mm + report]
```

The default character target is 38 mm, with a hard 45 mm ceiling unless explicitly changed. Characters have no integrated base and fit a separate 32 mm base. Relevant visual or geometry defects block delivery.

## Get started

```powershell
git clone https://github.com/eep0x10/critforge.git "$HOME/.codex/skills/meshy-miniaturas"
Set-Location "$HOME/.codex/skills/meshy-miniaturas"
python -m pip install -r requirements-mesh.txt
python scripts/workflow.py doctor
```

Store `MESHY_API_KEY` in the environment or a secret manager, outside chat and Git. The client never prints it.

Meshy's Multi-Image endpoint currently supports geometry up to 2K. The 4K default uses the approved front view for geometry and keeps rear/face images as mandatory QA references. Use `--mode multi-image-2k` only when multi-view consistency has priority over 4K.

## Documentation

The detailed operational guides are maintained in Portuguese:

- [Quick start](docs/QUICKSTART.md)
- [Skill instructions](SKILL.md)
- [API and recovery](references/commands.md)
- [Mesh review](references/mesh.md)
- [Contributing](CONTRIBUTING.md)

Private projects, models, character images, signed URLs, API responses, and credentials never belong in the public repository.

[MIT license](LICENSE) · [Report an issue](https://github.com/eep0x10/critforge/issues) · [Contribute](CONTRIBUTING.md)

Independent project, not affiliated with Meshy. The code license does not grant rights to third-party characters or models.
