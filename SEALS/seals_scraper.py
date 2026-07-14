import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pdfplumber

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")


SITE_URL = "https://seven-seals.com/"
CURRENT_FILE = os.path.join(os.path.dirname(__file__), "seals_schedule.json")
ARCHIVE_FILE = os.path.join(os.path.dirname(__file__), "seals_schedule_archive.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}
JST = timezone(timedelta(hours=9))

# 날짜 토큰: 7/8, 7/6-7, (8/3), *7/9, "-", "--", "TBA"
DATE_TOKEN = re.compile(r"^\(?\*?\d{1,2}/\d{1,2}(?:-\d{1,2})?\)?$")

# 일본 출항 포트 (헤더에서 이 이름들의 x좌표를 찾아 열로 사용)
DEPARTURE_PORTS = [
    "Hitachinaka",
    "Kisarazu",
    "Yokohama",
    "Nagoya",
    "Senboku",
    "Kobe",
    "Hibiki",
    "Moji",
    "Oita",
]
ARRIVAL_PORT = "Hambantota"


class RoroLinkParser(HTMLParser):
    HREF_PATTERN = re.compile(r"RORO-Shipping-Schedule.*\.pdf$", re.IGNORECASE)

    def __init__(self):
        super().__init__()
        self.current_href = None
        self.current_text = []
        self.pdf_url = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []
            if self.current_href and self.HREF_PATTERN.search(self.current_href):
                self.pdf_url = urljoin(SITE_URL, self.current_href)

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href:
            text = " ".join(self.current_text).strip().upper()
            if not self.pdf_url and "RORO SHIPPING SCHEDULE" in text:
                self.pdf_url = urljoin(SITE_URL, self.current_href)
            self.current_href = None
            self.current_text = []


def download(url, timeout=60):
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def get_roro_pdf_url():
    parser = RoroLinkParser()
    parser.feed(download(SITE_URL, timeout=30).decode("utf-8", errors="replace"))
    if parser.pdf_url:
        return parser.pdf_url

    raise RuntimeError(
        "seven-seals.com에서 RORO Shipping Schedule PDF 링크를 찾지 못했습니다."
    )


def find_updated_date(text, pdf_url):
    match = re.search(
        r"Last\s+update:\s*(\d{4})/(\d{1,2})/(\d{1,2})", text, re.IGNORECASE
    )
    if match:
        return date(*(int(value) for value in match.groups()))

    match = re.search(r"-(\d{4})(\d{2})(\d{2})\.pdf", pdf_url)
    if match:
        return date(*(int(value) for value in match.groups()))

    return datetime.now(JST).date()


def normalize_date(value, updated_date):
    value = value.strip().strip("()").lstrip("*")
    match = re.match(r"^(\d{1,2})/(\d{1,2})", value)
    if not match:
        return "-"

    month, day = (int(value) for value in match.groups())
    candidates = []
    for year in range(updated_date.year - 1, updated_date.year + 2):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        candidates.append(candidate)

    if not candidates:
        return "-"

    resolved = min(candidates, key=lambda candidate: abs(candidate - updated_date))
    return resolved.isoformat()


def center(word):
    return (word["x0"] + word["x1"]) / 2


def find_sections(words, page_height):
    """'FOR ...' 제목 행을 기준으로 페이지를 섹션으로 나눈다."""
    tops = sorted(
        word["top"]
        for word in words
        if word["text"] == "FOR" and word["x0"] < 20
    )
    sections = []
    for index, top in enumerate(tops):
        bottom = tops[index + 1] if index + 1 < len(tops) else page_height
        title_words = sorted(
            [word for word in words if abs(word["top"] - top) <= 2],
            key=lambda word: word["x0"],
        )
        title = " ".join(word["text"] for word in title_words)
        sections.append({"title": title, "top": top, "bottom": bottom})
    return sections


def parse_section(section, words, updated_date, pdf_url):
    section_words = [
        word for word in words if section["top"] < word["top"] < section["bottom"]
    ]

    # 선박 행: 따옴표로 시작하는 선명 단어가 앵커
    name_starts = sorted(
        [
            word
            for word in section_words
            if word["x0"] < 100 and word["text"].startswith('"')
        ],
        key=lambda word: word["top"],
    )
    if not name_starts:
        return []

    # 헤더 영역(섹션 제목 ~ 첫 선박 행)에서 포트 열 x좌표 수집
    header_bottom = name_starts[0]["top"] - 2
    columns = {}
    for word in section_words:
        if word["top"] >= header_bottom:
            continue
        name = word["text"]
        if name == ARRIVAL_PORT or name in DEPARTURE_PORTS:
            columns[name] = center(word)

    # Hambantota 열이 없는 섹션(스리랑카 미기항)은 건너뛴다
    if ARRIVAL_PORT not in columns:
        return []

    records = []
    for anchor in name_starts:
        record = parse_vessel_row(
            section, anchor, section_words, columns, updated_date, pdf_url
        )
        if record:
            records.append(record)
    return records


def parse_vessel_row(section, anchor, section_words, columns, updated_date, pdf_url):
    row_top = anchor["top"]
    row_words = sorted(
        [word for word in section_words if abs(word["top"] - row_top) <= 3],
        key=lambda word: word["x0"],
    )

    # 선명: 여는 따옴표 단어부터 닫는 따옴표 단어까지
    name_words = []
    voyage = None
    for word in row_words:
        if word["x0"] < anchor["x0"]:
            continue
        if not name_words and not word["text"].startswith('"'):
            continue
        if name_words and voyage is None and not name_words[-1].endswith('"'):
            name_words.append(word["text"])
            continue
        if not name_words:
            name_words.append(word["text"])
            continue
        # 선명 다음의 첫 숫자 토큰이 항차
        if voyage is None and re.match(r"^\d+[A-Z]?$", word["text"]):
            voyage = word["text"]
            break

    if not name_words or voyage is None:
        return None

    ship_name = " ".join(name_words).strip('"').replace('" ', " ").replace(' "', " ")
    ship_name = ship_name.replace('"', "").strip()

    # 날짜 토큰을 가장 가까운 포트 열에 매칭
    values = {}
    for word in row_words:
        if not DATE_TOKEN.match(word["text"]):
            continue
        word_center = center(word)
        nearest = min(columns, key=lambda port: abs(columns[port] - word_center))
        if abs(columns[nearest] - word_center) > 15:
            continue
        values[nearest] = normalize_date(word["text"], updated_date)

    hambantota = values.get(ARRIVAL_PORT, "-")
    if hambantota == "-":
        return None

    departures = {
        port: values.get(port, "-") for port in DEPARTURE_PORTS if port in columns
    }
    identity_date = next(
        (value for value in departures.values() if value != "-"), hambantota
    )

    service = re.sub(r"^FOR\s+", "", section["title"]).strip()
    return {
        "Service": service,
        "Company": "SEALS",
        "Ship Name": ship_name,
        "Voyage": voyage,
        "id": f"SEALS|{ship_name}|{voyage}|{identity_date}",
        "Departure Ports": departures,
        "Arrival Ports": {ARRIVAL_PORT: hambantota},
        "Source PDF": pdf_url,
        "Schedule Updated": updated_date.isoformat(),
    }


def parse_schedule(pdf_content, pdf_url):
    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
        if not pdf.pages:
            raise RuntimeError("RORO PDF에 페이지가 없습니다.")
        page = pdf.pages[0]
        text = page.extract_text() or ""
        words = page.extract_words(x_tolerance=1, y_tolerance=2, keep_blank_chars=False)
        page_height = page.height

    updated_date = find_updated_date(text, pdf_url)
    records = []
    seen = set()
    for section in find_sections(words, page_height):
        for record in parse_section(section, words, updated_date, pdf_url):
            key = (record["Ship Name"], record["Voyage"])
            if key in seen:
                continue
            seen.add(key)
            records.append(record)

    if not records:
        raise RuntimeError("RORO PDF에서 Hambantota 스케줄을 읽지 못했습니다.")
    return records


def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def update_files(current_records):
    previous_records = load_json(CURRENT_FILE)
    archive_records = load_json(ARCHIVE_FILE)
    current_ids = {record["id"] for record in current_records}
    archive_by_id = {record["id"]: record for record in archive_records}

    for record in previous_records:
        if record["id"] not in current_ids:
            archive_by_id[record["id"]] = record

    archive = sorted(
        archive_by_id.values(),
        key=lambda record: (
            next(
                (
                    value
                    for value in record.get("Departure Ports", {}).values()
                    if value != "-"
                ),
                "9999-12-31",
            ),
            record.get("Ship Name", ""),
        ),
    )
    save_json(CURRENT_FILE, current_records)
    save_json(ARCHIVE_FILE, archive)


def main():
    pdf_url = get_roro_pdf_url()
    print(f"RORO PDF: {pdf_url}")
    records = parse_schedule(download(pdf_url), pdf_url)
    update_files(records)
    for record in records:
        departures = ", ".join(
            f"{port} {value}"
            for port, value in record["Departure Ports"].items()
            if value != "-"
        )
        print(
            f"{record['Ship Name']} {record['Voyage']}: {departures} "
            f"-> Hambantota {record['Arrival Ports']['Hambantota']}"
        )
    print(f"Hambantota 스케줄 {len(records)}건 저장 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"SEALS 스케줄 크롤링 실패: {error}", file=sys.stderr)
        raise
