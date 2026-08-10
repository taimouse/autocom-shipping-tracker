import json
import os
import re
import sys
from collections import defaultdict
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


SCHEDULE_URL = "https://www.ycsco.com/schedule"
CURRENT_FILE = os.path.join(os.path.dirname(__file__), "nyk_schedule.json")
ARCHIVE_FILE = os.path.join(os.path.dirname(__file__), "nyk_schedule_archive.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
}
JST = timezone(timedelta(hours=9))

# 스크랩 대상 항로. 값은 schedule 페이지 카드의 <p class="en-title"> 와 일치해야
# 하고, 그대로 JSON의 "Service" 값이 된다(기존 레코드 id와의 연속성).
#
# 전 항로가 들어 있는 ALL PDF 대신 항로별 PDF를 쓴다. 항로별 PDF가 더 정확하다:
# 2026-08-07 기준으로 ALL PDF에는 SRI LANKA의 PROMETHEUS LEADER 080 항차가
# 통째로 빠져 있었고, AFRICA Osaka의 '8/12-8/14' 같은 적재 기간 표기도 ALL
# PDF에서는 열 간격에 눌려 읽히지 않았다.
ROUTES = ["AFRICA", "SRI LANKA"]

# 적재항(일본) 판별용. 여기에 없는 항구는 도착항으로 본다. 항로별 PDF는 열
# 구성을 헤더에서 그대로 읽어오므로, 목적항이 늘어나도 코드를 고칠 필요는
# 없다. 반대로 새로운 일본 적재항이 등장하면 여기에 추가해야 하며 그때는
# parse_route()가 경고를 남긴다.
JAPAN_PORTS = {
    "chiba",
    "hakata",
    "hiroshima",
    "hitachinaka",
    "imabari",
    "kanda",
    "kawasaki",
    "kisarazu",
    "kobe",
    "mizushima",
    "moji",
    "nagoya",
    "nakanoseki",
    "osaka",
    "sakaide",
    "sendai",
    "shimizu",
    "tokyo",
    "tomakomai",
    "toyohashi",
    "ube",
    "yokkaichi",
    "yokohama",
}

# '8/5', '*9/17', '8/12-8/14', '8/12-14', '--', '-', 'TBA'
DATE_TOKEN = re.compile(
    r"^\*?(?:--|-|TBA|\d{1,2}/\d{1,2}(?:-\d{1,2}(?:/\d{1,2})?)?)$",
    re.IGNORECASE,
)
VOYAGE_TOKEN = re.compile(r"^[A-Z0-9-]{2,}$")

# 헤더는 VESSEL/VOY 줄을 기준으로 위아래 한 줄씩 더 쓴다(항구명과 터미널명이
# 두 줄로 나뉘고 한 줄짜리 이름은 가운데 줄에 놓인다). 표 첫 행까지의 여백보다
# 좁게 잡아야 선박 행이 헤더로 딸려 들어오지 않는다.
HEADER_BAND = 30
# 같은 열의 단어 묶음(예: 'Port' + 'Louis')과 옆 열 사이를 가르는 x 간격.
# 2026-08 PDF 기준 열 안쪽 최대 간격은 4pt, 열 사이 최소 간격은 25pt다.
COLUMN_GAP = 15
ROW_BAND = 3


class RouteCardParser(HTMLParser):
    """schedule 페이지의 항로 카드에서 이름 / 게시일 / PDF 링크를 뽑는다.

    카드 구조 (2026-08 기준):
        <div class="item">
          <div class="head js-accordion">
            <p class="en-title">AFRICA</p>
          <div class="bottom">
            <p class="date-wrap"><span class="date">2026.8.7</span></p>
            <p class="pdf-button"><a href="...africa-260807.pdf" class="pdf">

    링크 텍스트는 전부 "PDF"라 이름으로는 구분할 수 없고, 파일명도
    'africa-260807.pdf' / 'REVISED-sri-lanka-260803.pdf' 처럼 접두사가 붙는
    경우가 있어 마크업 기준으로 찾는다. ALL 카드(<div class="item all">)도 같은
    규칙에 걸리지만 en-title이 "ALL"이라 ROUTES와 매칭되지 않는다.
    """

    DATE_TEXT = re.compile(r"(\d{4})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})")

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.div_depth = 0
        self.card = None
        self.capture = None  # (kind, tag)
        self.buffer = []
        self.cards = []

    @staticmethod
    def _classes(attrs):
        return set((attrs.get("class") or "").split())

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
        classes = self._classes(attrs)

        if tag == "div":
            self.div_depth += 1
            if self.card is None and "item" in classes:
                self.card = {
                    "depth": self.div_depth,
                    "name": None,
                    "date": None,
                    "url": None,
                }
            return

        if self.card is None:
            return

        if tag == "p" and "en-title" in classes:
            self.capture = ("name", "p")
            self.buffer = []
        elif tag == "span" and "date" in classes:
            self.capture = ("date", "span")
            self.buffer = []
        elif tag == "a" and not self.card["url"]:
            href = attrs.get("href") or ""
            if href.lower().endswith(".pdf"):
                self.card["url"] = urljoin(self.base_url, href)

    def handle_data(self, data):
        if self.capture:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if self.capture and self.capture[1] == tag:
            kind = self.capture[0]
            text = re.sub(r"\s+", " ", " ".join(self.buffer)).strip()
            if kind == "name":
                self.card["name"] = text.upper()
            else:
                match = self.DATE_TEXT.search(text)
                if match:
                    try:
                        self.card["date"] = date(*(int(v) for v in match.groups()))
                    except ValueError:
                        pass
            self.capture = None
            self.buffer = []

        if tag == "div":
            if self.card and self.card["depth"] == self.div_depth:
                if self.card["name"] and self.card["url"]:
                    self.cards.append(self.card)
                self.card = None
            self.div_depth = max(0, self.div_depth - 1)


def download(url, timeout=60):
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def download_page(url, timeout=60):
    """본문과 리다이렉트 이후의 최종 URL을 함께 돌려준다."""
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read(), response.geturl()


def pdf_url_date(pdf_url):
    """PDF 파일명의 YYMMDD를 게시일로 해석한다."""
    match = re.search(r"-(\d{2})(\d{2})(\d{2})(?:-\d+)?\.pdf", pdf_url)
    if not match:
        return None
    year, month, day = (int(value) for value in match.groups())
    try:
        return date(2000 + year, month, day)
    except ValueError:
        return None


def get_route_cards():
    """ROUTES에 있는 항로의 {name, url, date}를 순서대로 돌려준다."""
    content, final_url = download_page(SCHEDULE_URL, timeout=30)
    parser = RouteCardParser(final_url)
    parser.feed(content.decode("utf-8", errors="replace"))

    by_name = {}
    for card in parser.cards:
        by_name.setdefault(card["name"], card)

    missing = [name for name in ROUTES if name not in by_name]
    if missing:
        raise RuntimeError(
            f"schedule 페이지에서 항로 카드를 찾지 못했습니다: {', '.join(missing)}"
        )

    cards = []
    for name in ROUTES:
        card = dict(by_name[name])
        # 파일명 날짜를 우선한다. 카드의 <span class="date">는 재업로드 시
        # 갱신되지 않는 경우가 있어 보조로만 쓴다.
        card["published"] = pdf_url_date(card["url"]) or card["date"]
        cards.append(card)
    return cards


def extract_words(pdf_content):
    with pdfplumber.open(BytesIO(pdf_content)) as pdf:
        if not pdf.pages:
            raise RuntimeError("PDF에 페이지가 없습니다.")
        return pdf.pages[0].extract_words(
            x_tolerance=1, y_tolerance=2, keep_blank_chars=False
        )


def find_updated_date(words, pdf_url):
    """PDF 우상단의 'AS OF 2026/8/7' 을 스케줄 기준일로 읽는다."""
    text = " ".join(word["text"] for word in words)
    for pattern in (
        r"AS\s+OF\s+(\d{4})/(\d{1,2})/(\d{1,2})",
        r"\[\s*(\d{4})/(\d{1,2})/(\d{1,2})\s+Updated\s*\]",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return date(*(int(value) for value in match.groups()))
            except ValueError:
                continue

    return pdf_url_date(pdf_url) or datetime.now(JST).date()


def normalize_date(value, updated_date):
    """'8/5' / '*9/17' / '8/12-8/14' 를 ISO 날짜로 바꾼다.

    적재 기간(8/12-8/14)은 시작일만 남긴다. JSON 계약이 값 하나짜리 날짜
    문자열이고, index.html이 이 값을 그대로 정렬·달력 표시에 쓰기 때문이다.
    """
    value = value.strip().lstrip("*")
    if value.upper() in {"-", "--", "TBA"}:
        return "-"

    match = re.match(r"^(\d{1,2})/(\d{1,2})", value)
    if not match:
        return "-"

    month, day = (int(value) for value in match.groups())
    candidates = []
    for year in range(updated_date.year - 1, updated_date.year + 2):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue

    if not candidates:
        return "-"

    resolved = min(candidates, key=lambda candidate: abs(candidate - updated_date))
    return resolved.isoformat()


def find_anchor(words, text):
    for word in words:
        if word["text"].upper() == text:
            return word
    return None


def center(word):
    return (word["x0"] + word["x1"]) / 2


def port_kind(name):
    """항구명을 적재항/도착항으로 나눈다."""
    base = re.sub(r"\(.*?\)", " ", name).lower()
    tokens = re.sub(r"[^a-z]", " ", base).split()
    return "departure" if any(token in JAPAN_PORTS for token in tokens) else "arrival"


def build_columns(words, vessel_word, voy_word):
    """헤더에서 항구 열(이름 + 중심 x)을 순서대로 뽑는다.

    값이 열 중앙에 정렬되어 있어 x0가 아니라 중심 좌표로 맞춘다. 항구명이
    'Yokohama' + '(Daikoku)' 처럼 두 줄로 나뉘면 위->아래, 왼쪽->오른쪽 순으로
    이어붙인다.
    """
    band = sorted(
        (
            word
            for word in words
            if abs(word["top"] - vessel_word["top"]) <= HEADER_BAND
            and word["x0"] > voy_word["x1"] + 5
        ),
        key=lambda word: word["x0"],
    )

    groups = []
    for word in band:
        if groups and word["x0"] - max(item["x1"] for item in groups[-1]) <= COLUMN_GAP:
            groups[-1].append(word)
        else:
            groups.append([word])

    columns = []
    for group in groups:
        label = " ".join(
            item["text"]
            for item in sorted(group, key=lambda item: (round(item["top"]), item["x0"]))
        )
        x0 = min(item["x0"] for item in group)
        x1 = max(item["x1"] for item in group)
        name = re.sub(r"\s+", " ", label).strip()
        columns.append({"name": name, "center": (x0 + x1) / 2, "kind": port_kind(name)})
    return columns


def column_tolerance(columns):
    """날짜를 열에 붙일 때 허용할 최대 중심 편차 = 열 간격의 절반."""
    centers = sorted(column["center"] for column in columns)
    gaps = [right - left for left, right in zip(centers, centers[1:])]
    return min(gaps) / 2 if gaps else 60


def parse_vessel_row(service, columns, tolerance, row_words, voy_word, updated_date):
    ship_words = sorted(
        (word for word in row_words if word["x1"] < voy_word["x0"] - 5),
        key=lambda word: word["x0"],
    )
    if not ship_words:
        return None

    departures = {
        column["name"]: "-" for column in columns if column["kind"] == "departure"
    }
    arrivals = {
        column["name"]: "-" for column in columns if column["kind"] == "arrival"
    }

    updated = False
    for word in row_words:
        if word["x0"] <= voy_word["x1"] or not DATE_TOKEN.match(word["text"]):
            continue
        nearest = min(columns, key=lambda column: abs(column["center"] - center(word)))
        if abs(nearest["center"] - center(word)) > tolerance:
            continue
        if word["text"].startswith("*"):
            updated = True
        target = departures if nearest["kind"] == "departure" else arrivals
        target[nearest["name"]] = normalize_date(word["text"], updated_date)

    if all(value == "-" for value in {**departures, **arrivals}.values()):
        return None

    ship_name = " ".join(word["text"] for word in ship_words)
    identity_date = next(
        (value for value in departures.values() if value != "-"),
        next((value for value in arrivals.values() if value != "-"), "undated"),
    )

    return {
        "Service": service,
        "Company": "NYK",
        "Ship Name": ship_name,
        "Voyage": voy_word["text"],
        "id": f"NYK|{service}|{ship_name}|{voy_word['text']}|{identity_date}",
        "Updated": updated,
        "Departure Ports": departures,
        "Arrival Ports": arrivals,
    }


def parse_route(service, pdf_content, pdf_url):
    words = extract_words(pdf_content)
    updated_date = find_updated_date(words, pdf_url)

    vessel_word = find_anchor(words, "VESSEL")
    voy_word = find_anchor(words, "VOY")
    if not vessel_word or not voy_word:
        raise RuntimeError(f"{service}: PDF에서 VESSEL/VOY 헤더를 찾지 못했습니다.")

    columns = build_columns(words, vessel_word, voy_word)
    if not columns:
        raise RuntimeError(f"{service}: PDF 헤더에서 항구 열을 찾지 못했습니다.")
    if not any(column["kind"] == "departure" for column in columns):
        raise RuntimeError(
            f"{service}: 적재항으로 인식된 열이 없습니다 -> "
            f"{', '.join(column['name'] for column in columns)}"
        )

    tolerance = column_tolerance(columns)
    body_top = vessel_word["top"] + HEADER_BAND
    voy_center = center(voy_word)
    voyage_words = sorted(
        (
            word
            for word in words
            if word["top"] > body_top
            and abs(center(word) - voy_center) <= tolerance
            and VOYAGE_TOKEN.match(word["text"])
        ),
        key=lambda word: word["top"],
    )

    records = []
    for voyage_word in voyage_words:
        row_words = [
            word for word in words if abs(word["top"] - voyage_word["top"]) <= ROW_BAND
        ]
        record = parse_vessel_row(
            service, columns, tolerance, row_words, voyage_word, updated_date
        )
        if record:
            record["Source PDF"] = pdf_url
            record["Schedule Updated"] = updated_date.isoformat()
            records.append(record)

    if not records:
        raise RuntimeError(f"{service}: PDF에서 선박 스케줄을 읽지 못했습니다.")
    return records, columns


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


def stored_sources(records):
    """직전 실행이 항로별로 어떤 PDF를 저장했는지 돌려준다."""
    sources = defaultdict(set)
    for record in records:
        if record.get("Source PDF"):
            sources[record.get("Service")].add(record["Source PDF"])
    return sources


def skip_reason(cards, records):
    """모든 항로가 직전 실행과 같은 PDF면 건너뛸 이유를 돌려준다."""
    if not records:
        return None

    sources = stored_sources(records)
    unchanged = [
        card["name"] for card in cards if card["url"] in sources.get(card["name"], ())
    ]
    if len(unchanged) == len(cards):
        return f"모든 항로의 PDF가 직전 실행과 동일합니다 ({', '.join(unchanged)})"
    return None


def main():
    force = "--force" in sys.argv[1:]
    cards = get_route_cards()
    for card in cards:
        published = card["published"]
        print(
            f"{card['name']}: {card['url']} "
            f"(게시일 {published.isoformat() if published else '알 수 없음'})"
        )

    previous_records = load_json(CURRENT_FILE)
    reason = skip_reason(cards, previous_records)
    if reason and not force:
        print(f"업데이트 없음 - 스크래핑을 건너뜁니다: {reason}")
        return
    if reason:
        print(f"[--force] 건너뛰기 조건 무시: {reason}")

    records = []
    for card in cards:
        route_records, columns = parse_route(
            card["name"], download(card["url"]), card["url"]
        )
        records.extend(route_records)
        ports = " | ".join(
            f"{column['name']}({column['kind'][:3]})" for column in columns
        )
        print(f"{card['name']}: 선박 {len(route_records)}건 - {ports}")

    update_files(records)
    print(f"{len(cards)}개 항로, 선박 스케줄 {len(records)}건 저장 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"NYK 스케줄 크롤링 실패: {error}", file=sys.stderr)
        raise
