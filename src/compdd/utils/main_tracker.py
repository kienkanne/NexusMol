def main_tracker(cfg, stage_name, checkpoint=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = cfg.common.logger
            manifest = cfg.common.manifest
            runstate = cfg.common.runstate   

            if checkpoint and runstate.is_done(stage_name):
                logger.info(f"STAGE: {stage_name} already done, skipping")
                return runstate.get_output(stage_name)

            try:
                logger.info(f"STAGE: {stage_name} started")
                manifest.stage_start(stage_name)
                runstate.mark_running(stage_name)

                result = func(*args, **kwargs)

                runstate.mark_done(stage_name, result if checkpoint else None)
                manifest.stage_done(stage_name)
                logger.info(f"STAGE: {stage_name} completed")

            except Exception as e:
                runstate.mark_failed(stage_name)
                manifest.stage_failed(stage_name, e)
                logger.exception(f"STAGE: {stage_name} failed")
                manifest.finalize(success=False)
                raise

            return result
        return wrapper
    return decorator