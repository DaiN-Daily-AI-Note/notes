"""HWPX 표를 원본 칸 좌표로 다시 읽어 '펼친 표'로 내보낸다.

다인 DaiN 2026-11-17 회차 「AI가 한글 공문서 표를 깨짐 없이 읽을까」에서 쓴 보정 코드.

왜 필요한가 (정부 보도자료 HWPX에서 실제로 본 것):
1. 작성자가 줄 맞춤용으로 1pt 크기 글자("15")를 칸 안에 넣어 둠 → 그대로 읽으면 '1515-34세'.
2. 칸 병합이 줄 높이에 기대어 있음 → 한 묶음의 마지막 줄이 다음 묶음 시작 행과 겹쳐,
   병합을 그대로 옮기면 엉뚱한 묶음으로 보임.

보정:
1. 글자 모양(charPr) 크기가 MIN_HEIGHT(3pt) 미만인 글자는 버린다.
2. cellAddr/cellSpan으로 표를 격자로 펼친 뒤, 숫자 칸이 '시작하는' 행만 데이터 행으로 내보낸다.
   각 행에 왼쪽 묶음 이름을 다시 채워, 병합 없이도 뜻이 통하게 한다.

안전:
- 파이썬 표준 라이브러리만 쓴다. 네트워크·외부 명령·파일 쓰기(-o로 지정한 결과 파일 제외) 없음.
- 압축 폭탄 방지: 읽는 XML 하나당 압축 해제 크기 MAX_XML_BYTES, 합계 MAX_TOTAL_BYTES 상한.
- XML 폭탄 방지: DOCTYPE/ENTITY 선언이 있는 XML은 거부한다(HWPX에는 필요 없음).

사용: python3 hwpx_table_fix.py 문서.hwpx [-o 결과.md]
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

MIN_HEIGHT = 300  # HWPX 글자 크기 단위는 1/100pt → 3pt 미만은 간격 맞춤용으로 본다
MAX_XML_BYTES = 50 * 1024 * 1024  # XML 하나 압축 해제 상한 50MB
MAX_TOTAL_BYTES = 200 * 1024 * 1024  # 읽는 XML 합계 상한 200MB
MAX_DIM = 10_000  # 표 한 변(행 또는 열) 상한
MAX_CELLS = 1_000_000  # 표 격자 칸 수(행×열) 상한 — 작은 파일이 큰 표를 선언해 메모리를 고갈시키는 것 방지
NUMBER_CELL = re.compile(r"\(?[△+\-]?\d[\d,.]*%?\)?")
_DTD = re.compile(r"<!(DOCTYPE|ENTITY)", re.IGNORECASE)


class UnsafeDocument(ValueError):
    """크기 상한을 넘거나 DTD/엔티티가 든 문서."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


@dataclass
class Cell:
    row: int
    col: int
    row_span: int
    col_span: int
    text: str

    @property
    def is_number(self) -> bool:
        return bool(NUMBER_CELL.fullmatch(self.text))


@dataclass
class Table:
    n_rows: int
    n_cols: int
    cells: list[Cell] = field(default_factory=list)

    def _grid(self) -> list[list[Cell | None]]:
        grid: list[list[Cell | None]] = [[None] * self.n_cols for _ in range(self.n_rows)]
        for c in self.cells:
            for r in range(c.row, min(c.row + c.row_span, self.n_rows)):
                for k in range(c.col, min(c.col + c.col_span, self.n_cols)):
                    grid[r][k] = c
        return grid

    def _row_texts(self, grid: list[list[Cell | None]], r: int) -> list[str]:
        out: list[str] = []
        prev: Cell | None = None
        for c in grid[r]:
            if c is None or c is prev:
                continue
            prev = c
            if c.text:
                out.append(c.text)
        return out

    @property
    def rows(self) -> list[list[str]]:
        """펼친 격자의 모든 행 (병합 칸 글자를 덮인 행마다 다시 채움)."""
        grid = self._grid()
        return [self._row_texts(grid, r) for r in range(self.n_rows)]

    def data_rows(self) -> list[list[str]]:
        """숫자 칸이 그 행에서 시작하는 행만. 병합으로 이어진 '계속 행'은 중복이라 뺀다."""
        grid = self._grid()
        starts = {c.row for c in self.cells if c.is_number}
        return [self._row_texts(grid, r) for r in range(self.n_rows) if r in starts]


class _Budget:
    def __init__(self) -> None:
        self.used = 0

    def read(self, z: zipfile.ZipFile, name: str) -> bytes:
        info = z.getinfo(name)
        if info.file_size > MAX_XML_BYTES or self.used + info.file_size > MAX_TOTAL_BYTES:
            raise UnsafeDocument(f"압축 해제 크기 상한 초과: {name} ({info.file_size} bytes)")
        with z.open(info) as f:
            data = f.read(MAX_XML_BYTES + 1)  # 헤더 크기 값을 믿지 않고 실제로도 잘라 읽는다
        if len(data) > MAX_XML_BYTES:
            raise UnsafeDocument(f"압축 해제 크기 상한 초과: {name}")
        self.used += len(data)
        if self.used > MAX_TOTAL_BYTES:
            raise UnsafeDocument("압축 해제 합계 상한 초과")
        try:
            text = data.decode("utf-8")  # HWPX는 UTF-8. UTF-16 등으로 DTD 검사를 피해 가는 것을 막는다
        except UnicodeDecodeError as e:
            raise UnsafeDocument(f"UTF-8이 아닌 XML은 읽지 않습니다: {name}") from e
        if _DTD.search(text):
            raise UnsafeDocument(f"DTD/엔티티 선언이 든 XML은 읽지 않습니다: {name}")
        return data


def _char_heights(root: ET.Element) -> dict[str, int]:
    return {el.get("id"): int(el.get("height", "1000")) for el in root.iter() if _local(el.tag) == "charPr"}


def _cell_text(tc: ET.Element, heights: dict[str, int]) -> str:
    """칸 글자. 칸 안의 다른 표(중첩 표) 글자는 넣지 않는다."""
    parts: list[str] = []

    def walk(el: ET.Element) -> None:
        for ch in el:
            name = _local(ch.tag)
            if name == "tbl":
                continue
            if name == "run":
                if heights.get(ch.get("charPrIDRef", ""), 1000) < MIN_HEIGHT:
                    continue
                parts.append("".join(t.text or "" for t in ch.iter() if _local(t.tag) == "t"))
                continue
            if name == "p" and parts:
                parts.append(" ")
            walk(ch)

    walk(tc)
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _int(value: str | None, what: str) -> int:
    try:
        return int(value or "0")
    except ValueError as e:
        raise UnsafeDocument(f"숫자가 아닌 {what}: {value!r}") from e


def _parse_table(tbl: ET.Element, heights: dict[str, int]) -> Table:
    n_rows, n_cols = _int(tbl.get("rowCnt"), "rowCnt"), _int(tbl.get("colCnt"), "colCnt")
    if not (0 <= n_rows <= MAX_DIM and 0 <= n_cols <= MAX_DIM and n_rows * n_cols <= MAX_CELLS):
        raise UnsafeDocument(f"표 크기 상한 초과: {n_rows}행 x {n_cols}열")
    t = Table(n_rows, n_cols)
    for tr in tbl:
        if _local(tr.tag) != "tr":
            continue
        for tc in tr:
            if _local(tc.tag) != "tc":
                continue
            addr = next(e for e in tc if _local(e.tag) == "cellAddr")
            span = next(e for e in tc if _local(e.tag) == "cellSpan")
            r, c = _int(addr.get("rowAddr"), "rowAddr"), _int(addr.get("colAddr"), "colAddr")
            rs, cs = _int(span.get("rowSpan", "1"), "rowSpan"), _int(span.get("colSpan", "1"), "colSpan")
            if not (0 <= r < n_rows and 0 <= c < n_cols and rs >= 1 and cs >= 1):
                raise UnsafeDocument(f"표 밖의 칸 좌표: 행 {r}, 열 {c}")
            t.cells.append(Cell(r, c, rs, cs, _cell_text(tc, heights)))
    return t


def read_tables(path: str | Path) -> list[Table]:
    budget = _Budget()
    with zipfile.ZipFile(path) as z:
        heights = _char_heights(ET.fromstring(budget.read(z, "Contents/header.xml")))
        sections = sorted((n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)),
                          key=lambda n: int(re.sub(r"\D", "", n)))
        tables: list[Table] = []
        for name in sections:
            root = ET.fromstring(budget.read(z, name))
            tables.extend(_parse_table(el, heights) for el in root.iter() if _local(el.tag) == "tbl")
    return tables


def to_records(t: Table) -> tuple[list[str], list[dict[str, list[str]]]]:
    """숫자 칸 열마다 머리글을 붙인 기록으로 바꾼다.
    머리글 = 그 열을 덮는 머리글 칸 글자(위→아래, 중복 제거). 칸 값이 전부 괄호면 '증감'을 붙인다.
    기록 = {'labels': 그 행의 이름 칸들(묶음 → 항목), 'values': 머리글 순서의 값}."""
    grid = t._grid()
    first_data = min((c.row for c in t.cells if c.is_number), default=t.n_rows)
    starts = sorted({c.row for c in t.cells if c.is_number})
    value_cols = sorted({c.col for c in t.cells if c.is_number})
    heads: list[str] = []
    for col in value_cols:
        seen: list[str] = []
        for r in range(first_data):
            cell = grid[r][col]
            if cell and cell.text and cell.text not in seen:
                seen.append(cell.text)
        vals = [grid[r][col].text for r in starts if grid[r][col] and grid[r][col].is_number]
        head = " ".join(seen) or f"열{col}"
        if vals and all(v.startswith("(") for v in vals) and "증감" not in head:
            head += " 증감"
        heads.append(head)
    recs: list[dict[str, list[str]]] = []
    for r in starts:
        labels: list[str] = []
        prev: Cell | None = None
        for c in grid[r]:
            if c is None or c is prev:
                continue
            prev = c
            if c.text and not c.is_number:
                labels.append(c.text)
        values = [grid[r][col].text if grid[r][col] and grid[r][col].is_number else "" for col in value_cols]
        recs.append({"labels": labels, "values": values})
    return heads, recs


def to_markdown(t: Table) -> str:
    heads, recs = to_records(t)
    if not recs:
        return ""
    n_lab = max(len(r["labels"]) for r in recs)
    cols = ["구분"] * n_lab + heads
    lines = ["| " + " | ".join(cols) + " |", "|" + " --- |" * len(cols)]
    for r in recs:
        labs = [""] * (n_lab - len(r["labels"])) + r["labels"]
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in labs + r["values"]) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="HWPX 표를 원본 칸 좌표로 다시 읽어 마크다운 표로 내보낸다.")
    ap.add_argument("hwpx")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    md = "\n\n".join(m for m in (to_markdown(t) for t in read_tables(args.hwpx)) if m)
    if args.out:
        Path(args.out).write_text(md + "\n", encoding="utf-8")
    else:
        print(md)


if __name__ == "__main__":
    main()
