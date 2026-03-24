# pyright: reportAttributeAccessIssue=false
"""Biosignal Processing Pipeline CLI."""

from __future__ import annotations

from typing import Optional

import typer

app = typer.Typer(
    name="biosignal",
    help="Biosignal Processing Pipeline",
    add_completion=False,
)

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


@app.command()
def run(
    stage: int = typer.Argument(1, help="Stage number (1-10)"),
    subject: Optional[int] = typer.Option(None, help="Process specific subject only"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Run a pipeline stage."""
    import importlib

    typer.echo(f"Running stage {stage}: {STAGE_NAMES.get(stage, 'unknown')}")

    if stage == 1:
        acquisition = importlib.import_module("biosignal.stages.01_acquisition")
        acquisition.run(subject_id=subject, verbose=verbose)
    else:
        typer.echo(f"Stage {stage} not yet implemented", err=True)


@app.command()
def list_stages() -> None:
    """List all available pipeline stages."""
    typer.secho("Available stages:", bold=True)
    for num, name in STAGE_NAMES.items():
        typer.echo(f"  {num}. {name}")


@app.command()
def info(
    subject: Optional[int] = typer.Option(None, help="Subject ID"),
) -> None:
    """Show dataset information."""
    from biosignal.io.ieee import list_subjects, load
    from typing import cast

    subjects = list_subjects()
    typer.secho("IEEE Multimodal Biosignal Dataset", bold=True, fg=typer.colors.CYAN)
    typer.echo(f"Total subjects: {len(subjects)}")
    typer.echo(f"Subject IDs: {subjects}")

    if subject is not None:
        if subject not in subjects:
            typer.echo(f"Subject {subject} not found", err=True)
            raise typer.Exit(code=1)

        data = load(subject)
        typer.secho(f"\nSubject {subject:03d}:", bold=True)
        for modality in ["eeg", "ecg", "emg", "fnirs"]:
            if modality in data:
                info_data = data[modality]
                ch_names = cast(list[str], info_data["ch_names"])
                typer.echo(
                    f"  {modality.upper()}: {info_data['sfreq']} Hz, {len(ch_names)} ch"
                )


if __name__ == "__main__":
    app()
