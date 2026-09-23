import os


def write_tistory_draft(dir_path: str, filename: str, title: str, html: str) -> str:
    """티스토리에 수동으로 붙여넣을 제목+HTML을 파일로 저장하고 경로를 반환한다."""
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"<!-- 제목: {title} -->\n{html}")
    return path
