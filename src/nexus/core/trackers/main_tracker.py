from pydantic import BaseModel
from typing import Any, Optional


def main_tracker(stage_name, checkpoint=False):
    """
    NOTE: Main tracker logging ignores the --silence flag, as it is meant to track the main stages of a pipeline regardless of logging level
    This decorator wraps a function to automatically log its execution as a stage in the pipeline, with optional checkpointing.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            ctx = TrackerContext.get_ctx()

            logger = ctx.logger
            manifest = ctx.manifest
            runstate = ctx.runstate   

            if checkpoint and runstate.is_done(stage_name):
                logger.info(f"STAGE: {stage_name} already done, skipping", extra={"is_tracker": True})
                return runstate.get_output(stage_name)

            try:
                logger.info(f"STAGE: {stage_name} started", extra={"is_tracker": True})
                manifest.stage_start(stage_name)
                runstate.mark_running(stage_name)

                result = func(*args, **kwargs)

                runstate.mark_done(stage_name, result if checkpoint else None)
                manifest.stage_done(stage_name)
                logger.info(f"STAGE: {stage_name} completed", extra={"is_tracker": True})

            except Exception as e:
                runstate.mark_failed(stage_name)
                manifest.stage_failed(stage_name, e)
                logger.exception(f"STAGE: {stage_name} failed", extra={"is_tracker": True})
                manifest.finalize(success=False)
                raise

            return result
        return wrapper
    return decorator

class TrackerContext(BaseModel):
    logger: Optional[Any] = None
    manifest: Optional[Any] = None
    runstate: Optional[Any] = None

    # internal class variable to store instance
    # hint is user read only
    _active_context: "Optional[TrackerContext]" = None

    @classmethod
    def set_ctx(cls, ctx: "TrackerContext"):
        cls._active_context = ctx

    @classmethod
    def get_ctx(cls):
        if cls._active_context is None:
            raise RuntimeError("No currently active context")
        return cls._active_context


from nexus.core.trackers.logging_utils import CustomLogger
from nexus.core.trackers.manifest import Manifest
from nexus.core.trackers.runstate import RunState


def setup_context(scratch_dir, job_name):
    TrackerContext.set_ctx(TrackerContext(
        logger = CustomLogger(scratch_dir / f"{job_name}_run.log"),
        manifest = Manifest(scratch_dir / f"{job_name}_manifest.json"),
        runstate = RunState(scratch_dir / f"{job_name}_state.json")
    ))


def final_copy_trackers(output_dir):
    """
    Mark a pipeline completed and copy trackers to results directory
    """
    from pathlib import Path
    import shutil
    ctx = TrackerContext.get_ctx()
    logger = ctx.logger
    manifest = ctx.manifest
    runstate = ctx.runstate

    manifest.finalize(success=True)
    logger.info("Pipeline completed", extra={"is_tracker": True})

    log_path = logger.get_path()
    manifest_path = manifest.get_path()
    runstate_path = runstate.get_path()

    for src in (log_path, manifest_path, runstate_path):
        dst = output_dir / Path(src).name
        if src.exists():
            shutil.copy2(src, dst)

    return True
