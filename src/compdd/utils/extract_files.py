from pathlib import Path

def extract_files(input_inputs, pattern):
    """
    Accepts a single file path, a folder path, or a list of file/folder paths.
    """
    # 1. Normalize the input into a list of Path objects
    if isinstance(input_inputs, (str, Path)):
        input_list = [Path(input_inputs)]
    elif isinstance(input_inputs, list):
        input_list = [Path(p) for p in input_inputs]
    else:
        raise TypeError("Input must be a string path, Path object, or a list of them.")

    # 2. Resolve folders into individual file paths
    final_file_list = []
    for path in input_list:
        if not path.exists():
            print(f"Warning: Path does not exist, skipping: {path}")
            continue

        if path.is_dir():
            # Find all .sdf files in the folder (case-insensitive)
            # Use path.rglob('*.sdf') instead if you want to search subfolders recursively
            folder_sdfs = sorted(list(path.glob(f'*{pattern}')))
            final_file_list.extend(folder_sdfs)
        else:
            final_file_list.append(path)
    
    return final_file_list
