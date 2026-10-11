# Development Setup

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m kurocode
```

## Useful commands

```bash
python -m pytest -q
python scripts/build.py --output dist
python scripts/release.py --version 0.1.0
```
