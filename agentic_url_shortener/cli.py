import json
from typing import Annotated

import typer

from .config import Settings
from .database import Database
from .workflow import WorkflowService
from .evaluation import AgenticEvaluationSuite


app = typer.Typer(help="Operate the governed agentic SDLC workflow.")


def service() -> WorkflowService:
    settings = Settings()
    database = Database(settings.database_path)
    database.initialize()
    return WorkflowService(settings, database)


def show(value: dict | list) -> None:
    typer.echo(json.dumps(value, indent=2, default=str))


@app.command("run")
def run(requirement: str, scenario: str = "greenfield") -> None:
    """Start a run and execute until its first governed interrupt."""
    show(service().start(requirement, scenario))  # type: ignore[arg-type]


@app.command("inspect")
def inspect_run(run_id: str, events: bool = False) -> None:
    engine = service()
    show(engine.events(run_id) if events else engine.get(run_id))


@app.command()
def approve(run_id: str, action: str, actor: str = "reviewer") -> None:
    show(service().approve(run_id, action, True, actor))


@app.command()
def reject(run_id: str, action: str, actor: str = "reviewer") -> None:
    show(service().approve(run_id, action, False, actor))


@app.command()
def resume(run_id: str, clarification: str) -> None:
    show(service().resume(run_id, clarification))


@app.command()
def cancel(run_id: str) -> None:
    show(service().cancel(run_id))


SCENARIOS = {
    "greenfield": "Build a URL shortener with create and redirect APIs",
    "brownfield": "Add expiration and redirect analytics to the existing URL service",
    "ambiguous": "make shared links safer",
}


@app.command()
def demo(
    scenario: Annotated[str, typer.Argument(help="greenfield, brownfield, or ambiguous")]
) -> None:
    """Start one deterministic interview scenario."""
    if scenario not in SCENARIOS:
        raise typer.BadParameter("Choose greenfield, brownfield, or ambiguous")
    show(service().start(SCENARIOS[scenario], scenario))  # type: ignore[arg-type]


@app.command()
def evaluate(output: str = "eval-results.json") -> None:
    """Run deterministic governance evaluations and write stable JSON evidence."""
    report = AgenticEvaluationSuite().run_and_write(__import__("pathlib").Path(output))
    show(report.model_dump())
    if report.failed:
        raise typer.Exit(code=1)
