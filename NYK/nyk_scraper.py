import difflib
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
from pypdf import PdfReader

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
DATE_TOKEN = re.compile(r"^(?:--|-|TBA|\*?\d{1,2}/\d{1,2}(?:-\d{1,2})?)$")


def port(name, x, kind):
    """항구 열 정의.

    name은 JSON 출력 키이자 index.html이 참조하는 계약이라 코드에 유지한다.
    x는 실제 열 위치를 PDF 헤더에서 찾지 못했을 때만 쓰는 폴백값이다
    (resolve_ports 참고). PDF 여백이 밀려도 깨지지 않도록 평소에는
    헤더에서 유도한 좌표를 쓴다.
    """
    return {"name": name, "x": x, "kind": kind}


SERVICES = [
    {
        "name": "JEBEL ALI (PG)",
        "token": "JEBEL",
        "ports": [
            port("Yokohama", 365, "departure"),
            port("Nagoya (Kinjyo)", 434, "departure"),
            port("Kobe", 509, "departure"),
            port("Yokohama (Second Call)", 567, "departure"),
            port("Kawasaki", 632, "departure"),
            port("Jebel Ali", 705, "arrival"),
            port("Hamad", 750, "arrival"),
            port("Bahrain", 809, "arrival"),
            port("Dammam", 869, "arrival"),
            port("Kuwait", 934, "arrival"),
            port("Sohar", 993, "arrival"),
        ],
    },
    {
        "name": "KARACHI",
        "token": "KARACHI",
        "ports": [
            port("Yokohama", 365, "departure"),
            port("Nagoya (Kinjyo)", 434, "departure"),
            port("Kobe", 509, "departure"),
            port("Yokohama (Second Call)", 567, "departure"),
            port("Kawasaki", 632, "departure"),
            port("Karachi", 694, "arrival"),
        ],
    },
    {
        "name": "SRI LANKA",
        "token": "SRI",
        "ports": [
            port("Yokohama", 365, "departure"),
            port("Osaka", 437, "departure"),
            port("Kobe", 509, "departure"),
            port("Nagoya (Kinjyo)", 574, "departure"),
            port("Kawasaki", 632, "departure"),
            port("Moji", 702, "departure"),
            port("Sri Lanka (Hambantota)", 808, "arrival"),
        ],
    },
    {
        "name": "AFRICA",
        "token": "AFRICA",
        "ports": [
            port("Yokohama", 365, "departure"),
            port("Osaka", 437, "departure"),
            port("Kobe", 509, "departure"),
            port("Nagoya (Kinjyo)", 574, "departure"),
            port("Kawasaki", 632, "departure"),
            port("Moji", 702, "departure"),
            port("Mombasa", 805, "arrival"),
            port("Dar Es Salaam", 884, "arrival"),
            port("Durban", 933, "arrival"),
            port("Port Louis", 995, "arrival"),
            port("Lagos", 1047, "arrival"),
            port("Tema", 1106, "arrival"),
            port("Abidjan", 1164, "arrival"),
        ],
    },
    {
        "name": "RED SEA",
        "token": "RED",
        "ports": [
            port("Kobe", 377, "departure"),
            port("Yokohama", 427, "departure"),
            port("Nagoya", 504, "departure"),
            port("Kawasaki", 569, "departure"),
            port("Jeddah", 638, "arrival"),
            port("Aqaba", 697, "arrival"),
            port("Port Sudan", 755, "arrival"),
            port("Djibouti", 809, "arrival"),
        ],
    },
    {
        "name": "CARIB (下旬)",
        "token": "CARIB",
        "ports": [
            port("Kawasaki", 367, "departure"),
            port("Yokohama", 427, "departure"),
            port("Nagoya", 504, "departure"),
            port("Kobe", 579, "departure"),
            port("Osaka", 638, "departure"),
        ],
    },
    {
        "name": "IQUIQUE (SOUTH AMERICA)",
        "token": "IQUIQUE",
        "ports": [
            port("Nagoya", 434, "departure"),
            port("Yokohama", 497, "departure"),
            port("Pt. Quetzal", 629, "arrival"),
            port("Acajutla", 691, "arrival"),
            port("Callao", 751, "arrival"),
            port("Iquique", 811, "arrival"),
            port("San Antonio", 882, "arrival"),
        ],
    },
    {
        "name": "CENTRAL AMERICA",
        "token": "CENTRAL",
        "ports": [
            port("Osaka", 437, "departure"),
            port("Yokohama", 497, "departure"),
            port("Nagoya", 574, "departure"),
            port("Pt. Quetzal", 631, "arrival"),
            port("Acajutla", 694, "arrival"),
            port("San Lorenzo", 757, "arrival"),
            port("Corinto", 811, "arrival"),
            port("Pt. Caldera", 884, "arrival"),
            port("Lazaro Cardenas", 935, "arrival"),
            port("Buenaventura", 992, "arrival"),
        ],
    },
    {
        "name": "CANADA",
        "token": "CANADA",
        "ports": [
            port("Kawasaki", 430, "departure"),
            port("Yokohama", 497, "departure"),
            port("Nagoya", 574, "departure"),
            port("New Westminster (Vancouver)", 653, "arrival"),
        ],
    },
    {
        "name": "NAWC (北米西岸)",
        "token": "NAWC",
        "ports": [
            port("Kawasaki", 430, "departure"),
            port("Yokohama", 497, "departure"),
            port("Nagoya", 574, "departure"),
            port("Port Hueneme", 631, "arrival"),
            port("Los Angeles", 703, "arrival"),
            port("Tacoma", 747, "arrival"),
        ],
    },
    {
        "name": "NAEC (北米東岸)",
        "token": "NAEC",
        "ports": [
            port("Nagoya", 434, "departure"),
            port("Yokohama", 497, "departure"),
            port("Kawasaki", 569, "departure"),
            port("Jacksonville", 625, "arrival"),
            port("Baltimore", 689, "arrival"),
        ],
    },
    {
        "name": "HONOLULU",
        "token": "HONOLULU",
        "ports": [
            port("Yokohama", 427, "departure"),
            port("Nagoya", 504, "departure"),
            port("Honolulu", 633, "arrival"),
        ],
    },
    {
        "name": "EUROPE",
        "token": "EUROPE",
        "ports": [
            port("Kobe", 377, "departure"),
            port("Nagoya (Kinjyo)", 434, "departure"),
            port("Nagoya (Nishisanku)", 504, "departure"),
            port("Yokohama", 567, "departure"),
            port("Osaka", 638, "departure"),
        ],
    },
    {
        "name": "WEST AUST",
        "token": "WEST",
        "ports": [
            port("Nagoya (Kinjo)", 372, "departure"),
            port("Nagoya (Nishisanku)", 434, "departure"),
            port("Yokohama", 497, "departure"),
            port("Fremantle", 633, "arrival"),
            port("Darwin", 695, "arrival"),
        ],
    },
    {
        "name": "EAST AUST",
        "token": "EAST",
        "ports": [
            port("Nagoya (Kinjo)", 372, "departure"),
            port("Nagoya (Nishisanku)", 434, "departure"),
            port("Yokohama", 497, "departure"),
            port("Osaka", 576, "departure"),
            port("Kobe", 641, "departure"),
            port("Townsville", 686, "arrival"),
            port("Brisbane", 745, "arrival"),
            port("Port Kembla", 809, "arrival"),
            port("Melbourne", 866, "arrival"),
            port("Adelaide", 930, "arrival"),
        ],
    },
    {
        "name": "PNG",
        "token": "PNG",
        "ports": [
            port("Nagoya", 372, "departure"),
            port("Yokohama", 427, "departure"),
            port("Guam", 640, "arrival"),
            port("Lae", 703, "arrival"),
            port("Port Moresby", 755, "arrival"),
        ],
    },
    {
        "name": "BANGLA",
        "token": "BANGLA",
        "ports": [
            port("Nakanoseki", 363, "departure"),
            port("Moji", 441, "departure"),
            port("Kobe", 509, "departure"),
            port("Osaka", 576, "departure"),
            port("Nagoya", 636, "departure"),
            port("Yokohama", 688, "departure"),
            port("Kawasaki", 744, "departure"),
            port("Singapore", 804, "arrival"),
            port("Chittagong", 865, "arrival"),
            port("Mongla", 933, "arrival"),
        ],
    },
    {
        "name": "ASIA",
        "token": "ASIA",
        "ports": [
            port("Nakanoseki (Hakata, Moji)", 365, "departure"),
            port("Kobe", 439, "departure"),
            port("Osaka", 506, "departure"),
            port("Yokohama", 567, "departure"),
            port("Nagoya (Nishisanku)", 636, "departure"),
            port("Taipei", 697, "arrival"),
            port("Shanghai", 745, "arrival"),
            port("Singapore", 804, "arrival"),
            port("Port Kelang (North)", 874, "arrival"),
            port("Port Kelang (West)", 935, "arrival"),
            port("Ho Chi Minh", 1000, "arrival"),
            port("Haiphong", 1040, "arrival"),
            port("Jakarta", 1101, "arrival"),
        ],
    },
    {
        "name": "SOUTH PACIFIC",
        "token": "SOUTH",
        "ports": [
            port("Kobe", 377, "departure"),
            port("Nagoya", 434, "departure"),
            port("Yokohama", 497, "departure"),
            port("Honiara", 573, "arrival"),
            port("Santo", 640, "arrival"),
            port("Port Vila", 703, "arrival"),
            port("Noumea", 747, "arrival"),
            port("Lautoka", 808, "arrival"),
            port("Suva", 879, "arrival"),
            port("Nuku'Alofa", 936, "arrival"),
            port("Apia", 996, "arrival"),
            port("Pagopago", 1038, "arrival"),
            port("Tarawa", 1102, "arrival"),
        ],
    },
]


class ScheduleLinkParser(HTMLParser):
    """YCS schedule 페이지에서 ALL PDF 링크와 게시 날짜를 뽑아낸다.

    ALL PDF는 세 단계로 찾는다. 사이트 개편(2026-07)으로 링크 텍스트가 전부
    "PDF"가 되었고, 파일명도 all-260805.pdf -> revised-all-260807.pdf 처럼
    접두사가 붙는 경우가 있어 어느 한 방법만으로는 깨진다.

    1) <div class="item all"> 블록 안의 PDF 링크 (마크업 기준, 가장 안정적)
    2) 파일명이 (...-)all-YYMMDD(-N).pdf 인 링크 중 최신 날짜
    3) 링크 텍스트가 정확히 "ALL"인 링크

    각 항로 항목의 <span class="date">2026.8.7</span> 도 함께 수집한다.
    """

    # 'all-260805.pdf', 'revised-all-260807.pdf', 'all-260731-1.pdf' 모두 허용.
    # 워드프레스는 같은 날짜로 재업로드하면 -N 접미사를 붙인다.
    ALL_HREF = re.compile(r"(?:^|/|-)all-(\d{6})(?:-\d+)?\.pdf$", re.IGNORECASE)
    DATE_TEXT = re.compile(r"(\d{4})\s*[./-]\s*(\d{1,2})\s*[./-]\s*(\d{1,2})")

    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.current_href = None
        self.current_text = []
        self.candidates = []
        self.text_match_url = None
        self.item_all_url = None
        self.div_depth = 0
        self.all_item_depth = None
        self.date_depth = None
        self.span_depth = 0
        self.date_text = []
        self.dates = []

    @staticmethod
    def _classes(attrs):
        return set((dict(attrs).get("class") or "").split())

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "div":
            self.div_depth += 1
            classes = self._classes(attrs)
            if self.all_item_depth is None and {"item", "all"} <= classes:
                self.all_item_depth = self.div_depth
        elif tag == "span":
            self.span_depth += 1
            if self.date_depth is None and "date" in self._classes(attrs):
                self.date_depth = self.span_depth
                self.date_text = []
        elif tag == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []
            if self.current_href:
                url = urljoin(self.base_url, self.current_href)
                match = self.ALL_HREF.search(self.current_href)
                if match:
                    self.candidates.append((match.group(1), url))
                if (
                    self.all_item_depth is not None
                    and not self.item_all_url
                    and self.current_href.lower().endswith(".pdf")
                ):
                    self.item_all_url = url

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)
        if self.date_depth is not None:
            self.date_text.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "div":
            if self.all_item_depth == self.div_depth:
                self.all_item_depth = None
            self.div_depth = max(0, self.div_depth - 1)
        elif tag == "span":
            if self.date_depth == self.span_depth:
                match = self.DATE_TEXT.search("".join(self.date_text))
                if match:
                    try:
                        self.dates.append(
                            date(*(int(value) for value in match.groups()))
                        )
                    except ValueError:
                        pass
                self.date_depth = None
            self.span_depth = max(0, self.span_depth - 1)
        elif tag == "a" and self.current_href:
            if not self.text_match_url and (
                " ".join(self.current_text).strip().upper() == "ALL"
            ):
                self.text_match_url = urljoin(self.base_url, self.current_href)
            self.current_href = None
            self.current_text = []

    @property
    def all_pdf_url(self):
        if self.item_all_url:
            return self.item_all_url
        if self.candidates:
            return max(self.candidates)[1]
        return self.text_match_url

    @property
    def latest_page_date(self):
        return max(self.dates) if self.dates else None


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


def get_all_pdf_info():
    """(ALL PDF URL, 사이트가 표시하는 갱신일)을 돌려준다.

    갱신일은 ALL PDF 파일명의 날짜를 우선한다. ALL 항목에는 날짜 배지가 없고
    각 항로 항목에만 <span class="date">가 붙는데, 그중에는 ALL PDF에 들어가지
    않는 항로(CONVENTIONAL SERVICES 등)도 있어 그대로 쓰면 과잉 감지가 된다.
    파일명에서 날짜를 못 읽을 때만 페이지 배지 최신값으로 폴백한다.
    """
    content, final_url = download_page(SCHEDULE_URL, timeout=30)
    parser = ScheduleLinkParser(final_url)
    parser.feed(content.decode("utf-8", errors="replace"))
    if not parser.all_pdf_url:
        raise RuntimeError(
            "YCS schedule page에서 SERVICE 'ALL' PDF 링크를 찾지 못했습니다."
        )

    published = pdf_url_date(parser.all_pdf_url) or parser.latest_page_date
    return parser.all_pdf_url, published


def extract_pdf_text(pdf_content):
    reader = PdfReader(BytesIO(pdf_content))
    return "\n".join(
        page.extract_text(extraction_mode="layout") or "" for page in reader.pages
    )


def extract_pdf_page(pdf_content):
    pdf = pdfplumber.open(BytesIO(pdf_content))
    if not pdf.pages:
        raise RuntimeError("ALL PDF에 페이지가 없습니다.")
    return pdf, pdf.pages[0]


def find_updated_date(text, pdf_url):
    match = re.search(
        r"\[\s*(\d{4})/(\d{1,2})/(\d{1,2})\s+Updated\s*\]",
        text,
        re.IGNORECASE,
    )
    if match:
        return date(*(int(value) for value in match.groups()))

    match = re.search(r"-(\d{2})(\d{2})(\d{2})(?:-\d+)?\.pdf", pdf_url)
    if match:
        year, month, day = (int(value) for value in match.groups())
        return date(2000 + year, month, day)

    return datetime.now(JST).date()


def normalize_date(value, updated_date):
    value = value.strip().lstrip("*")
    if value in {"-", "--", "TBA"}:
        return "-"

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


def find_service_tops(words):
    tops = {}
    for service in SERVICES:
        candidates = [
            word["top"]
            for word in words
            if word["x0"] < 100 and word["text"].upper() == service["token"]
        ]
        if candidates:
            tops[service["name"]] = min(candidates)
    return tops


# 헤더 텍스트 매칭 임계값. PDF 원본 오타(Townsville -> "Townsiville")와
# 전각괄호 인코딩 깨짐((Kinjo) -> 모지바케)을 흡수하되 다른 항구로 오매칭되지
# 않는 선. 항구명이 2~3줄에 걸쳐 있어 x구간이 이만큼 벌어지면 다른 열로 본다.
HEADER_MATCH_RATIO = 0.82
HEADER_COLUMN_GAP = 12


def normalize_label(text):
    """비교용으로 대소문자·공백·괄호·깨진 전각문자를 제거한다."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def locate_column(port_name, header_words):
    """헤더에서 port_name에 해당하는 단어 묶음을 찾아 x0를 돌려준다."""
    target = normalize_label(port_name)
    if not target:
        return None

    ordered = sorted(header_words, key=lambda word: word["x0"])
    best = None
    for start in range(len(ordered)):
        group = []
        span_end = None
        for word in ordered[start:]:
            if span_end is not None and word["x0"] - span_end > HEADER_COLUMN_GAP:
                break
            group.append(word)
            span_end = max(item["x1"] for item in group)
            # 여러 줄에 걸친 항구명은 위->아래, 왼쪽->오른쪽 순으로 이어붙인다
            label = normalize_label(
                " ".join(
                    item["text"]
                    for item in sorted(
                        group, key=lambda item: (round(item["top"]), item["x0"])
                    )
                )
            )
            if not label:
                continue
            ratio = difflib.SequenceMatcher(None, target, label).ratio()
            if best is None or ratio > best[0]:
                best = (ratio, min(item["x0"] for item in group))

    if best and best[0] >= HEADER_MATCH_RATIO:
        return best[1]
    return None


def resolve_ports(service, header_words):
    """서비스의 각 항구 열 위치를 헤더에서 유도한다.

    헤더에 없는 이름(예: 'Yokohama (Second Call)'처럼 우리가 붙인 구분용
    표기)은 하드코딩 폴백 x를 그대로 쓴다. 못 찾은 이름 목록도 함께 돌려준다.
    """
    resolved = []
    missing = []
    for item in service["ports"]:
        x = locate_column(item["name"], header_words)
        if x is None:
            missing.append(item["name"])
            x = item["x"]
        resolved.append({**item, "x": x})
    return {**service, "ports": resolved}, missing


def parse_vessel_row(service, voyage_word, words, updated_date, pdf_url):
    row_top = voyage_word["top"]
    row_words = [word for word in words if abs(word["top"] - row_top) <= 3]
    ship_words = sorted(
        [word for word in row_words if 95 <= word["x0"] < 300],
        key=lambda word: word["x0"],
    )
    if not ship_words:
        return None

    ship_name = " ".join(word["text"] for word in ship_words)
    voyage = voyage_word["text"]
    date_words = sorted(
        [
            word
            for word in row_words
            if word["x0"] >= 350 and DATE_TOKEN.match(word["text"])
        ],
        key=lambda word: word["x0"],
    )
    if not date_words:
        return None

    departures = {
        item["name"]: "-" for item in service["ports"] if item["kind"] == "departure"
    }
    arrivals = {
        item["name"]: "-" for item in service["ports"] if item["kind"] == "arrival"
    }

    for date_word in date_words:
        nearest = min(
            service["ports"], key=lambda item: abs(item["x"] - date_word["x0"])
        )
        if abs(nearest["x"] - date_word["x0"]) > 55:
            continue
        normalized = normalize_date(date_word["text"], updated_date)
        target = departures if nearest["kind"] == "departure" else arrivals
        # 일부 서비스에는 목적항 앞에 이름 없는 보조 열이 있다. 같은 항구에
        # 두 값이 매칭되면 뒤쪽의 실제 목적항 값을 사용한다.
        target[nearest["name"]] = normalized

    identity_date = next(
        (value for value in departures.values() if value != "-"),
        next((value for value in arrivals.values() if value != "-"), "undated"),
    )
    updated = any(
        word["text"] == "★"
        and word["x0"] < 100
        and abs(word["top"] - row_top) <= 3
        for word in words
    )

    return {
        "Service": service["name"],
        "Company": "NYK",
        "Ship Name": ship_name,
        "Voyage": voyage,
        "id": f"NYK|{service['name']}|{ship_name}|{voyage}|{identity_date}",
        "Updated": updated,
        "Departure Ports": departures,
        "Arrival Ports": arrivals,
        "Source PDF": pdf_url,
        "Schedule Updated": updated_date.isoformat(),
    }


def parse_all_schedules(pdf_content, pdf_url):
    text = extract_pdf_text(pdf_content)
    updated_date = find_updated_date(text, pdf_url)
    pdf, page = extract_pdf_page(pdf_content)
    try:
        words = page.extract_words(
            x_tolerance=1, y_tolerance=2, keep_blank_chars=False
        )
    finally:
        pdf.close()

    service_tops = find_service_tops(words)
    ordered_services = [
        service for service in SERVICES if service["name"] in service_tops
    ]
    records = []
    unresolved = []
    for index, service in enumerate(ordered_services):
        top = service_tops[service["name"]]
        bottom = (
            service_tops[ordered_services[index + 1]["name"]]
            if index + 1 < len(ordered_services)
            else page.height - 50
        )
        voyage_words = sorted(
            [
                word
                for word in words
                if top + 18 < word["top"] < bottom
                and 300 <= word["x0"] <= 345
                and re.match(r"^[A-Z0-9-]{2,}$", word["text"])
            ],
            key=lambda word: word["top"],
        )
        if not voyage_words:
            continue

        # 헤더 영역: 서비스 제목 줄 ~ 첫 선박 행 직전
        header_words = [
            word
            for word in words
            if top - 16 <= word["top"] < voyage_words[0]["top"] - 4
            and word["x0"] >= 340
        ]
        live_service, missing = resolve_ports(service, header_words)
        if missing:
            unresolved.append((service["name"], missing))

        for voyage_word in voyage_words:
            record = parse_vessel_row(
                live_service, voyage_word, words, updated_date, pdf_url
            )
            if record:
                records.append(record)

    for service_name, missing in unresolved:
        print(
            f"[warn] {service_name}: 헤더에서 열을 찾지 못해 폴백 좌표 사용 -> "
            f"{', '.join(missing)}",
            file=sys.stderr,
        )

    if not records:
        raise RuntimeError("ALL PDF에서 선박 스케줄을 읽지 못했습니다.")
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


def previous_state(records):
    """직전 실행이 어떤 PDF를 어느 갱신일로 저장했는지 돌려준다."""
    urls = {record.get("Source PDF") for record in records if record.get("Source PDF")}
    dates = []
    for record in records:
        value = record.get("Schedule Updated")
        if value:
            try:
                dates.append(date.fromisoformat(value))
            except ValueError:
                continue
    return urls, (max(dates) if dates else None)


def skip_reason(pdf_url, published, records):
    """스크래핑을 건너뛸 이유가 있으면 문자열로, 없으면 None을 돌려준다."""
    if not records:
        return None

    previous_urls, previous_date = previous_state(records)

    # 같은 파일을 다시 받는 것뿐이면 결과가 바뀔 수 없다.
    if pdf_url in previous_urls:
        return f"ALL PDF가 직전 실행과 동일합니다 ({pdf_url})"

    # 파일명은 달라졌지만(재업로드 등) 게시일이 더 과거면 새 스케줄이 아니다.
    if published and previous_date and published < previous_date:
        return (
            f"사이트 게시일 {published.isoformat()}이(가) "
            f"저장된 {previous_date.isoformat()}보다 과거입니다"
        )

    return None


def main():
    force = "--force" in sys.argv[1:]
    pdf_url, published = get_all_pdf_info()
    print(f"ALL PDF: {pdf_url}")
    print(f"사이트 게시일: {published.isoformat() if published else '알 수 없음'}")

    previous_records = load_json(CURRENT_FILE)
    reason = skip_reason(pdf_url, published, previous_records)
    if reason and not force:
        print(f"업데이트 없음 - 스크래핑을 건너뜁니다: {reason}")
        return
    if reason:
        print(f"[--force] 건너뛰기 조건 무시: {reason}")

    records = parse_all_schedules(download(pdf_url), pdf_url)
    update_files(records)
    service_count = len({record["Service"] for record in records})
    print(f"{service_count}개 서비스, 선박 스케줄 {len(records)}건 저장 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"NYK 스케줄 크롤링 실패: {error}", file=sys.stderr)
        raise
