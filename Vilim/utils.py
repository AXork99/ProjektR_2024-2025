def get_dir(file: str) -> str:
    f = file.split("\\")
    f.pop()
    return '/'.join(f) + "/"