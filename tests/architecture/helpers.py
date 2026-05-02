from pathlib import Path

from pytestarch import get_evaluable_architecture


def evaluable():
    project_root = Path(__file__).resolve().parents[2]
    return get_evaluable_architecture(
        root_path=str(project_root),
        module_path=str(project_root / "src"),
    )


def module_prefix() -> str:
    project_root = Path(__file__).resolve().parents[2]
    return f"{project_root.name}.src"
