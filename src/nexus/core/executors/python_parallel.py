import concurrent.futures
from nexus.core.trackers.logging_utils import DummyLogger
from nexus.core.trackers.main_tracker import TrackerContext

def _execute_parallel_task(task):
    """
    Must live at the top level of the module so workers can see it.
    Unwraps and executes the frozen task object.
    """
    if callable(task):
        return task()
    
    # Optional fallback: also supports raw tuples like (func, args_tuple, kwargs_dict)
    func, args, kwargs = task
    return func(*args, **kwargs)


from contextlib import contextmanager

@contextmanager
def python_parallel(tasks, n_jobs=1, title="", skip=False):
    try:
        ctx = TrackerContext.get_ctx()
        logger = ctx.logger if ctx.logger is not None else DummyLogger()
    except:
        logger = DummyLogger()

    logger.info(f"Running: Parallel {title} for {len(tasks)} jobs")
    results = [None] * len(tasks)
    
    # 3. Execute the frozen tasks in parallel
    with concurrent.futures.ProcessPoolExecutor(max_workers=n_jobs) as executor:
        future_to_index = {}
        
        for i, task in enumerate(tasks):
            # Ship the task to our top-level executor helper
            future = executor.submit(_execute_parallel_task, task)
            future_to_index[future] = i

        # 4. Gather results in original order
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                if skip:
                    # Log it, but don't re-raise. results[index] remains None.
                    logger.error(f"Task {index} failed with error: {e}. 'skip=True' is active, skipping task.")
                else:
                    # Strict behavior: log and crash the entire pipeline immediately
                    logger.error(f"Task {index} failed with error: {e}. Crashing pipeline.")
                    raise

    # --- Handling the downstream return strategy ---
    if skip:
        # Strategy A: Filter out None values so downstream doesn't process broken data
        filtered_results = [r for r in results if r is not None]
        logger.info(f"Python parallel execution completed. Kept {len(filtered_results)}/{len(tasks)} successful jobs.")
        yield filtered_results
    else:
        yield results