from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from api.errors import error_response
from api.responses import sanitize_for_public_response
from api.settings import resolve_runs_dir
from services.run_repository import RunRepository, RunRepositoryError

router = APIRouter(prefix="/v1/runs", tags=["runs"])
T = TypeVar("T")


@router.get("")
def list_runs(
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.list_runs(limit=limit),
    )


@router.get("/{run_id}")
def get_run(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_run(run_id),
    )


@router.delete("/{run_id}")
def delete_run(
    run_id: str,
    runs_dir: Annotated[str, Query()] = "runs",
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.delete_run(run_id),
    )


@router.get("/{run_id}/trace")
def get_run_trace(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_trace(run_id),
    )


@router.get("/{run_id}/result")
def get_run_result(
    run_id: str,
    runs_dir: str = Query(default="runs"),
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.get_result(run_id),
    )


@router.get("/{run_id}/artifacts")
def list_run_artifacts(
    run_id: str,
    runs_dir: Annotated[str, Query()] = "runs",
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> dict:
    return _run_repository_call(
        runs_dir,
        lambda repository: repository.list_artifacts(run_id, limit=limit),
    )


@router.get("/{run_id}/artifacts/{name:path}", response_class=FileResponse)
def get_run_artifact(
    run_id: str,
    name: str,
    runs_dir: str = Query(default="runs"),
) -> FileResponse:
    artifact_path = _run_repository_call(
        runs_dir,
        lambda repository: repository.resolve_artifact(run_id, name),
    )
    return FileResponse(artifact_path)


def _run_repository_call(runs_dir: str, callback: Callable[[RunRepository], T]) -> T:
    try:
        return sanitize_for_public_response(callback(RunRepository(resolve_runs_dir(runs_dir))))
    except RunRepositoryError as exc:
        raise error_response(exc.status_code, exc.code, exc.message) from exc
