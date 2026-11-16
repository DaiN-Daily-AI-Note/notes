"""hwpx_table_fix 시험. 실제 보도자료 파일 대신, 같은 구조(1pt 숨은 글자 + 줄 높이에 기댄 병합)를
가진 작은 HWPX를 시험 안에서 만들어 쓴다. 실행: python3 -m unittest test_hwpx_table_fix"""
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hwpx_table_fix as fix  # noqa: E402

NS = 'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
HEADER = f'<hh:head {NS}><hh:charPr id="1" height="1000"/><hh:charPr id="2" height="100"/></hh:head>'


def cell(r, c, text, rs=1, cs=1, spacer=""):
    runs = (f'<hp:run charPrIDRef="2"><hp:t>{spacer}</hp:t></hp:run>' if spacer else "") + \
           f'<hp:run charPrIDRef="1"><hp:t>{text}</hp:t></hp:run>'
    return (f'<hp:tc><hp:subList><hp:p>{runs}</hp:p></hp:subList>'
            f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/><hp:cellSpan colSpan="{cs}" rowSpan="{rs}"/></hp:tc>')


# 행 0 머리글, 고용률 = 1~2행, 고용률 15-34세 = 2~3행(줄 높이로 맞춤), 실업률 = 3~4행
ROWS = [
    [cell(0, 0, "구분", cs=2), cell(0, 2, "10월"), cell(0, 3, "증감")],
    [cell(1, 0, "고용률", rs=2), cell(1, 1, "15-29세"), cell(1, 2, "42.9"), cell(1, 3, "(△1.7)")],
    [cell(2, 1, "15-34세", rs=2, spacer="15"), cell(2, 2, "55.4", rs=2), cell(2, 3, "(△0.6)", rs=2)],
    [cell(3, 0, "실업률", rs=2)],
    [cell(4, 1, "15-34세"), cell(4, 2, "4.1"), cell(4, 3, "(△0.3)")],
]
SECTION = f'<hs:sec {NS} xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"><hp:p><hp:run><hp:tbl rowCnt="5" colCnt="4">' + \
    "".join(f"<hp:tr>{''.join(r)}</hp:tr>" for r in ROWS) + "</hp:tbl></hp:run></hp:p></hs:sec>"


def make_hwpx(path: Path, section: str = SECTION, header: str = HEADER) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Contents/header.xml", header)
        z.writestr("Contents/section0.xml", section)
    return path


class HwpxTableFixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.table = fix.read_tables(make_hwpx(self.dir / "a.hwpx"))[0]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_tiny_spacer_text_is_dropped(self) -> None:
        cells = [c for r in self.table.rows for c in r]
        self.assertIn("15-34세", cells)
        self.assertNotIn("1515-34세", cells)

    def test_row_keeps_its_own_group_when_merge_overlaps_next_group(self) -> None:
        rows = self.table.data_rows()
        self.assertEqual(rows, [
            ["고용률", "15-29세", "42.9", "(△1.7)"],
            ["고용률", "15-34세", "55.4", "(△0.6)"],
            ["실업률", "15-34세", "4.1", "(△0.3)"],
        ])

    def test_value_columns_get_headers(self) -> None:
        heads, recs = fix.to_records(self.table)
        self.assertEqual(heads, ["10월", "증감"])
        self.assertEqual(recs[1], {"labels": ["고용률", "15-34세"], "values": ["55.4", "(△0.6)"]})

    def test_markdown_output(self) -> None:
        md = fix.to_markdown(self.table)
        self.assertIn("| 고용률 | 15-34세 | 55.4 | (△0.6) |", md)
        self.assertIn("| 실업률 | 15-34세 | 4.1 | (△0.3) |", md)

    def test_rejects_xml_with_entity_declarations(self) -> None:
        bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;">]>' + SECTION
        with self.assertRaises(fix.UnsafeDocument):
            fix.read_tables(make_hwpx(self.dir / "bomb.hwpx", section=bomb))

    def test_rejects_huge_declared_table_before_allocating(self) -> None:
        huge = SECTION.replace('rowCnt="5" colCnt="4"', 'rowCnt="100000" colCnt="100000"')
        with self.assertRaises(fix.UnsafeDocument):
            fix.read_tables(make_hwpx(self.dir / "huge.hwpx", section=huge))

    def test_rejects_cell_outside_declared_table(self) -> None:
        bad = SECTION.replace('rowAddr="4"', 'rowAddr="99"')
        with self.assertRaises(fix.UnsafeDocument):
            fix.read_tables(make_hwpx(self.dir / "out.hwpx", section=bad))

    def test_rejects_utf16_xml_that_hides_entity_declarations(self) -> None:
        sneaky = '<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY a "XX">]>' + SECTION
        p = self.dir / "u16.hwpx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("Contents/header.xml", HEADER)
            z.writestr("Contents/section0.xml", sneaky.encode("utf-16"))
        with self.assertRaises(fix.UnsafeDocument):
            fix.read_tables(p)

    def test_rejects_oversized_member(self) -> None:
        old = fix.MAX_XML_BYTES
        fix.MAX_XML_BYTES = 1000
        try:
            big = SECTION.replace("</hs:sec>", "<!--" + "x" * 5000 + "--></hs:sec>")
            with self.assertRaises(fix.UnsafeDocument):
                fix.read_tables(make_hwpx(self.dir / "big.hwpx", section=big))
        finally:
            fix.MAX_XML_BYTES = old


if __name__ == "__main__":
    unittest.main()
