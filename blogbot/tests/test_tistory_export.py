import os

from tistory_export import write_tistory_draft


def test_write_tistory_draft_creates_file_with_title_comment_and_html(tmp_path):
    dir_path = tmp_path / "tistory_drafts"

    path = write_tistory_draft(str(dir_path), "2026-09-23-abc.html", "제목", "<p>본문</p>")

    content = open(path, encoding="utf-8").read()
    assert content == "<!-- 제목: 제목 -->\n<p>본문</p>"


def test_write_tistory_draft_creates_missing_directory(tmp_path):
    dir_path = tmp_path / "nested" / "tistory_drafts"

    path = write_tistory_draft(str(dir_path), "f.html", "t", "<p>b</p>")

    assert os.path.exists(path)
