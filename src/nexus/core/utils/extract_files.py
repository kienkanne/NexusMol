from pathlib import Path
from typing import Union, List

def extract_files(
    input_path: Union[str, Path, List[Union[str, Path]]], 
    patterns: Union[str, List[str]], 
    recursive: bool = False
) -> List[Path]:
    """
    Accepts exactly one file path, exactly one directory path, or a list of file paths.
    
    - If `input_path` is a file or a list of files, returns a list containing those files.
    - If `input_path` is a directory, returns child files matching `*{pattern}`.
    """
    # 1. Handle List of paths
    if isinstance(input_path, list):
        resolved_list = [Path(p) for p in input_path]
        
        # Enforce that all items in the list exist and are not directories
        for p in resolved_list:
            if not p.exists():
                raise FileNotFoundError(f"Path does not exist: {p}")
            if p.is_dir():
                raise TypeError(f"Input list contains a folder: {p}")
                
        return resolved_list

    # 2. Handle Single Path (str or Path object)
    if isinstance(input_path, (str, Path)):
        path = Path(input_path)
    else:
        raise TypeError("Input must be a file path, a folder path, or a list of file paths.")

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    # 3. Process Directory vs File
    if path.is_dir():
        # Clean up patterns: convert single string to a list of one string
        if isinstance(patterns, str):
            pattern_list = [patterns]
        elif isinstance(patterns, list):
            pattern_list = patterns
        else:
            raise TypeError(f"Invalid patterns type: {type(patterns)}. Must be str or list.")
        
        # Aggregate matches from all patterns without overwriting
        all_results = []
        for pat in pattern_list:
            glob_pattern = f"*{pat}"
            # Select generator based on recursion requirement
            matched_generator = path.rglob(glob_pattern) if recursive else path.glob(glob_pattern)
            
            # Filter for files immediately to avoid carrying directories forward
            all_results.extend([f for f in matched_generator if f.is_file()])
            
        return sorted(list(set(all_results))) # set() prevents duplicates if patterns overlap
        
    else:
        return [path]