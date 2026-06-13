import json
import os
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.request import Request, urlopen

SOURCE_URL = "https://www.bunkerindex.com/prices/port.php?p=109&n=busan-republic-of-korea"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "vlsfo_prices.json")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def get_kst_now():
    return datetime.now(timezone(timedelta(hours=9)))


def to_number(value):
    text = value.strip().replace(",", "").replace("%", "")
    if text in {"", "-", "n/a", "N/A"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def text_cells(row):
    return [" ".join(str(cell).split()) for cell in row]


def is_price_table(table):
    rows = table.get("rows", [])
    header = " ".join(text_cells(rows[0] if rows else [])).lower()
    return "date" in header and "price" in header and "low" in header and "high" in header


def table_to_records(table):
    records = []
    for row in table.get("rows", []):
        cells = text_cells(row)
        if len(cells) < 6 or not DATE_RE.match(cells[0]):
            continue

        records.append(
            {
                "date": cells[0],
                "year": int(cells[0][0:4]),
                "month": int(cells[0][5:7]),
                "price": to_number(cells[1]),
                "change": to_number(cells[2]),
                "change_percent": to_number(cells[3]),
                "low": to_number(cells[4]),
                "high": to_number(cells[5]),
                "source": SOURCE_URL,
            }
        )
    return records


class PriceTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self._table = None
        self._table_depth = 0
        self._row = None
        self._cell = None
        self._text_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self._flush_text()
            if self._table is None:
                self._table = {"class": attrs.get("class", ""), "rows": []}
                self._table_depth = 1
            else:
                self._table_depth += 1
        elif self._table is not None:
            if tag == "tr":
                self._row = []
            elif tag in {"th", "td"}:
                self._cell = []

    def handle_endtag(self, tag):
        if self._table is not None:
            if tag in {"th", "td"} and self._cell is not None and self._row is not None:
                self._row.append(" ".join("".join(self._cell).split()))
                self._cell = None
            elif tag == "tr" and self._row is not None:
                if any(cell for cell in self._row):
                    self._table["rows"].append(self._row)
                self._row = None
            elif tag == "table":
                self._table_depth -= 1
                if self._table_depth == 0:
                    self.elements.append({"type": "table", "table": self._table})
                    self._table = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)
        elif self._table is None:
            self._text_buffer.append(data)

    def close(self):
        self._flush_text()
        super().close()

    def _flush_text(self):
        text = " ".join("".join(self._text_buffer).split())
        if text:
            self.elements.append({"type": "text", "text": text})
        self._text_buffer = []


def parse_html_tables(html):
    parser = PriceTableParser()
    parser.feed(html)
    parser.close()
    return parser.elements


def find_vlsfo_spot_table(elements):
    heading_re = re.compile(r"Historical Spot Prices\s*\|\s*Busan:\s*VLSFO", re.I)
    for index, element in enumerate(elements):
        if element["type"] == "text" and heading_re.search(element["text"]):
            for previous in reversed(elements[:index]):
                if previous["type"] == "table" and is_price_table(previous["table"]):
                    return previous["table"]

    price_tables = [
        element["table"]
        for element in elements
        if element["type"] == "table"
        and "tablePrices1" in element["table"].get("class", "").split()
        and is_price_table(element["table"])
    ]
    if len(price_tables) >= 3:
        return price_tables[2]
    if price_tables:
        return price_tables[0]

    all_price_tables = [
        element["table"]
        for element in elements
        if element["type"] == "table" and is_price_table(element["table"])
    ]
    if len(all_price_tables) >= 3:
        return all_price_tables[2]
    if all_price_tables:
        return all_price_tables[0]

    raise RuntimeError("VLSFO price table was not found.")


def load_existing(path):
    if not os.path.exists(path):
        return {"metadata": {}, "records": []}
    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, list):
        return {"metadata": {}, "records": payload}
    return {"metadata": payload.get("metadata", {}), "records": payload.get("records", [])}


def merge_records(existing_records, scraped_records):
    by_date = {record.get("date"): record for record in existing_records if record.get("date")}
    for record in scraped_records:
        by_date[record["date"]] = record
    return sorted(by_date.values(), key=lambda item: item["date"], reverse=True)


def scrape_vlsfo_prices():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    request = Request(SOURCE_URL, headers=headers)
    with urlopen(request, timeout=30) as response:
        html = response.read().decode(response.headers.get_content_charset() or "utf-8", errors="replace")

    elements = parse_html_tables(html)
    table = find_vlsfo_spot_table(elements)
    records = table_to_records(table)
    if not records:
        raise RuntimeError("VLSFO table was found, but no price rows were parsed.")
    return records


def save_prices(path=OUTPUT_FILE):
    scraped_records = scrape_vlsfo_prices()
    existing = load_existing(path)
    records = merge_records(existing.get("records", []), scraped_records)
    now = get_kst_now().isoformat(timespec="seconds")

    payload = {
        "metadata": {
            "port": "Busan, Republic of Korea",
            "product": "VLSFO",
            "unit": "USD/MT",
            "source": SOURCE_URL,
            "last_updated": now,
            "record_count": len(records),
            "latest_date": records[0]["date"] if records else None,
        },
        "records": records,
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print(f"Saved {len(scraped_records)} scraped rows, {len(records)} total rows to {path}")


if __name__ == "__main__":
    save_prices()
