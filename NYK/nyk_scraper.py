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
    # 2026-07 사이트 개편으로 링크 텍스트가 전부 "PDF"로 바뀌어,
    # href 파일명(all-YYMMDD.pdf)으로 ALL PDF를 식별한다.
    ALL_HREF = re.compile(r"/all-\d{6}\.pdf$", re.IGNORECASE)

    def __init__(self):
        super().__init__()
        self.current_href = None
        self.current_text = []
        self.all_pdf_url = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.current_href = dict(attrs).get("href")
            self.current_text = []
            if self.current_href and self.ALL_HREF.search(self.current_href):
                self.all_pdf_url = urljoin(SCHEDULE_URL, self.current_href)

    def handle_data(self, data):
        if self.current_href:
            self.current_text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href:
            if not self.all_pdf_url and (
                " ".join(self.current_text).strip().upper() == "ALL"
            ):
                self.all_pdf_url = urljoin(SCHEDULE_URL, self.current_href)
            self.current_href = None
            self.current_text = []


def download(url, timeout=60):
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def get_all_pdf_url():
    parser = ScheduleLinkParser()
    parser.feed(download(SCHEDULE_URL, timeout=30).decode("utf-8", errors="replace"))
    if parser.all_pdf_url:
        return parser.all_pdf_url

    raise RuntimeError("YCS schedule page에서 SERVICE 'ALL' PDF 링크를 찾지 못했습니다.")


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

    match = re.search(r"-(\d{2})(\d{2})(\d{2})\.pdf", pdf_url)
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
        for voyage_word in voyage_words:
            record = parse_vessel_row(
                service, voyage_word, words, updated_date, pdf_url
            )
            if record:
                records.append(record)

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


def main():
    pdf_url = get_all_pdf_url()
    print(f"ALL PDF: {pdf_url}")
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
