"""CLI for Biosignal Processing Pipeline.

Usage:
    uv run python -m biosignal run 1
    uv run python -m biosignal run 2 --subject 5 --verbose
"""

from __future__ import annotations

from typing import Optional

import typer

from biosignal.io.ieee import list_subjects

app = typer.Typer(help="Biosignal Processing Pipeline")

STAGE_NAMES = {
    1: "acquisition",
    2: "sqi",
    3: "statistics",
    4: "cleaning",
    5: "segmentation",
    6: "features",
    7: "engineering",
    8: "dimreduction",
    9: "selection",
    10: "validation",
}

# Lazy imports for stages to avoid circular imports
_STAGE_FUNCTIONS: dict[int, callable] = {}


def _get_stage_func(stage: int):
    """Get stage function with lazy loading."""
    if stage not in _STAGE_FUNCTIONS:
        if stage == 1:
            from biosignal.stages import acquisition

            _STAGE_FUNCTIONS[stage] = acquisition.run
        elif stage == 2:
            from biosignal.stages import sqi

            _STAGE_FUNCTIONS[stage] = sqi.run
        else:
            raise ValueError(f"Stage {stage} not yet implemented")
    return _STAGE_FUNCTIONS[stage]


@app.command()
def run(
    stage: int = typer.Argument(1, help="Stage number (1-10)"),
    subject: Optional[int] = typer.Option(None, help="Process specific subject only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
):
    """Run a pipeline stage."""
    if stage < 1 or stage > 10:
        typer.secho(f"Error: Stage must be between 1 and 10", fg=typer.colors.RED)
        raise typer.Exit(1)

    stage_name = STAGE_NAMES.get(stage, "unknown")
    typer.echo(f"Running stage {stage}: {stage_name}")

    try:
        stage_func = _get_stage_func(stage)
        stage_func(subject_id=subject, verbose=verbose)
        typer.secho("Stage completed successfully!", fg=typer.colors.GREEN)
    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as e:
        typer.secho(f"Error running stage: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command()
def list_stages():
    """List all available pipeline stages."""
    typer.secho("Available stages:", bold=True)
    for num, name in STAGE_NAMES.items():
        typer.echo(f"  {num}. {name}")


@app.command()
def info(
    subject: Optional[int] = typer.Option(None, "--subject", "-s", help="Subject ID"),
):
    """Show dataset information."""
    try:
        subjects = list_subjects()
        typer.echo(f"Dataset: IEEE Multimodal Emotion Recognition")
        typer.echo(f"Available subjects: {len(subjects)}")
        typer.echo(f"Subject IDs: {subjects}")

        if subject is not None:
            if subject in subjects:
                typer.echo(f"\nSubject {subject:03d} is available")
            else:
                typer.secho(
                    f"Subject {subject:03d} not found in dataset", fg=typer.colors.YELLOW
                )
    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
