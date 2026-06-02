import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

def get_kst_now():
    """한국 표준시(KST)를 반환하는 함수. 시간 비교 오류를 막기 위해 naive datetime 객체를 반환합니다."""
    return datetime.now(timezone(timedelta(hours=9))).replace(tzinfo=None)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys

# Windows 환경에서 한글 출력 시 발생하는 UnicodeEncodeError 방지
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


# 사용법:
# python scraper.py          # 일반 크롤링 실행
# python scraper.py --test   # 이메일 설정 테스트

def send_notification_email(change_summary=None, route_name=None):
    """변경 사항 알림 이메일 전송

    Args:
        change_summary (str|None): 변경 사항 요약 문자열. None이면 간단한 알림만 전송.
        route_name (str|None): 라우트 이름 (예: "ASIA"). Subject에 포함.
    """
    try:
        # 이메일 설정 (아래 값들을 실제 값으로 변경하세요)
        sender_email = "jiworld.kim@gmail.com"  # 발신자 Gmail 주소
        receiver_emails = ["jiworld.kim@gmail.com", "ateam.marko@gmail.com"]  # 여러 수신자 이메일
        password = os.environ.get("EMAIL_PASSWORD")  # 환경변수에서 비밀번호 로드

        if not password:
            raise ValueError("환경 변수 EMAIL_PASSWORD가 설정되지 않았습니다.")

        # Gmail 앱 비밀번호 설정 방법:
        # 1. Google 계정 설정 → 보안 → 2단계 인증 켜기
        # 2. 보안 → 앱 비밀번호 생성 (선택: 메일, 기기: Windows 컴퓨터)
        # 3. 생성된 16자리 비밀번호를 password에 입력

        # 이메일 내용 구성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receiver_emails)  # 여러 수신자 표시
        subject_prefix = f"[{route_name}] " if route_name else ""
        msg['Subject'] = f"{subject_prefix}선박 운송 일정 변경 알림 - {get_kst_now().strftime('%Y-%m-%d %H:%M')}"

        # 이메일 본문에 변경 요약 포함 (있을 경우)
        now_text = get_kst_now().strftime('%Y년 %m월 %d일 %H시 %M분')
        body_lines = [
            "안녕하세요,",
            "",
            "선박 운송 일정에 변경 사항이 감지되었습니다.",
            "",
            f"변경 시간: {now_text}",
            "",
        ]

        if change_summary:
            # 너무 길면 자르기
            max_len = 4000
            summary = change_summary
            if len(summary) > max_len:
                summary = summary[:max_len] + "\n... (생략)"
            body_lines.append("변경 요약:")
            body_lines.append(summary)
            body_lines.append("")
            body_lines.append("전체 데이터는 shipping_update.json을 확인하세요.")
        else:
            body_lines.append("새로운 데이터를 확인하려면 shipping_update.json 파일을 확인해주세요.")

        body_lines.append("")
        body_lines.append("자동화 시스템")

        body = "\n".join(body_lines)

        msg.attach(MIMEText(body, 'plain'))

        # SMTP 서버 연결 및 이메일 전송 (여러 수신자)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)  # receiver_emails 리스트 전달
        server.quit()

        print("이메일 알림이 성공적으로 전송되었습니다.")

    except Exception as e:
        print(f"이메일 전송 실패: {e}")
def send_test_email():
    """테스트 이메일 전송"""
    try:
        # 이메일 설정 (아래 값들을 실제 값으로 변경하세요)
        sender_email = "jiworld.kim@gmail.com"  # 발신자 Gmail 주소
        receiver_emails = ["jiworld.kim@gmail.com", "rokgy85@gmail.com"]  # 여러 수신자 이메일
        password = os.environ.get("EMAIL_PASSWORD")  # 환경변수에서 비밀번호 로드

        if not password:
            raise ValueError("환경 변수 EMAIL_PASSWORD가 설정되지 않았습니다.")

        # 이메일 내용 구성
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join(receiver_emails)  # 여러 수신자 표시
        msg['Subject'] = f"선박 운송 일정 알림 시스템 테스트 - {get_kst_now().strftime('%Y-%m-%d %H:%M')}"

        body = f"""
테스트 이메일입니다.

선박 운송 일정 알림 시스템이 정상적으로 작동하고 있습니다.

테스트 시간: {get_kst_now().strftime('%Y년 %m월 %d일 %H시 %M분')}

이 메일이 정상적으로 수신되었다면 시스템 설정이 완료된 것입니다.

자동화 시스템
        """.strip()

        msg.attach(MIMEText(body, 'plain'))

        # SMTP 서버 연결 및 이메일 전송 (여러 수신자)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_emails, text)  # receiver_emails 리스트 전달
        server.quit()

        print("테스트 이메일이 성공적으로 전송되었습니다!")

    except Exception as e:
        print(f"테스트 이메일 전송 실패: {e}")
        print("\n※ Gmail 설정을 확인해주세요:")
        print("  1. sender_email과 password를 실제 Gmail 계정 정보로 변경")
        print("  2. Gmail 앱 비밀번호 생성 방법:")
        print("    - Google 계정 → 보안 → 2단계 인증 켜기")
        print("    - 보안 → 앱 비밀번호 생성 (메일/Windows 컴퓨터)")
        print("    - 생성된 16자리 비밀번호를 password에 입력")

def summarize_changes(old_data, new_data):
    """두 데이터 리스트를 비교하여 사람 읽기 좋은 변경 요약 문자열 반환."""
    if old_data is None:
        return f"초기 저장: 총 {len(new_data)}개의 선박 정보가 저장되었습니다."

    def key(item):
        return f"{item.get('Company','')}|{item.get('Ship Name','')}|{item.get('Voyage','')}"

    old_map = {key(item): item for item in old_data}
    new_map = {key(item): item for item in new_data}

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    added = new_keys - old_keys
    removed = old_keys - new_keys
    common = old_keys & new_keys

    lines = []
    if added:
        lines.append(f"추가된 선박: {len(added)}개")
        for k in sorted(added):
            parts = k.split('|')
            lines.append(f"  + {parts[0]} - {parts[1]} ({parts[2]})")

    if removed:
        lines.append(f"삭제된 선박: {len(removed)}개")
        for k in sorted(removed):
            parts = k.split('|')
            lines.append(f"  - {parts[0]} - {parts[1]} ({parts[2]})")

    # 변경된 항목 검사
    for k in sorted(common):
        o = old_map[k]
        n = new_map[k]
        sub_lines = []
        # 출발항 비교
        for port, old_val in o.get('Departure Ports', {}).items():
            new_val = n.get('Departure Ports', {}).get(port)
            if old_val != new_val:
                sub_lines.append(f"    출발 - {port}: '{old_val}' -> '{new_val}'")
        # 도착항 비교
        for port, old_val in o.get('Arrival Ports', {}).items():
            new_val = n.get('Arrival Ports', {}).get(port)
            if old_val != new_val:
                sub_lines.append(f"    도착 - {port}: '{old_val}' -> '{new_val}'")

        if sub_lines:
            parts = k.split('|')
            lines.append(f"변경: {parts[0]} - {parts[1]} ({parts[2]})")
            lines.extend(sub_lines)

    if not lines:
        return "변경 사항이 감지되었으나 요약할 차이점이 없습니다. 전체 파일을 확인하세요."

    return "\n".join(lines)

MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
# 선두의 'MonDD'만 취한다. 'Jun06Cut:May28'처럼 마감일이 붙어와도 출발일(Jun06)만 사용.
MONDD_RE = re.compile(r'^([A-Z][a-z]{2})(\d{1,2})')


def resolve_year(mon_idx, day, base, slack_past_days=60):
    """크롤링 시점(base)을 기준으로 연도를 확정한다.

    크롤링 사이트는 연도를 표시하지 않지만, 운송 보드는 항상 '현재~미래' 스케줄만
    노출한다(지난 스케줄은 아카이브로 빠짐). 따라서 약간의 과거(slack_past_days)만
    허용하는 12개월 전방 윈도우에 날짜를 끼워 넣어 연도를 정한다.

    예) 12월에 크롤링한 'Jan21'은 다음 해 1월로, 'Dec10'은 올해 12월로 확정 →
        연말→연초로 넘어가는 항차의 연도가 어긋나지 않는다.
    """
    base_date = base.date() if hasattr(base, 'date') else base
    for year in (base_date.year - 1, base_date.year, base_date.year + 1):
        try:
            d = datetime(year, mon_idx + 1, day).date()
        except ValueError:
            continue
        diff = (d - base_date).days
        if -slack_past_days <= diff <= (365 - slack_past_days):
            return year
    return base_date.year


def to_iso(date_str, base):
    """'Apr21' → '2026-04-21'. 이미 ISO이거나 '-'이면 그대로 둔다(idempotent)."""
    if not date_str or date_str == '-':
        return '-'
    if ISO_RE.match(date_str):
        return date_str
    m = MONDD_RE.match(date_str)
    if not m or m.group(1) not in MONTHS:
        return date_str
    mon_idx = MONTHS.index(m.group(1))
    day = int(m.group(2))
    year = resolve_year(mon_idx, day, base)
    try:
        return datetime(year, mon_idx + 1, day).strftime('%Y-%m-%d')
    except ValueError:
        return date_str


def make_id(ship):
    """[출발일-선명-보야드] 형식의 고유 ID. 출발일은 가장 빠른 ISO 출발일.

    출발일을 포함하므로 같은 선명·보야드가 다른 시기에 다시 등장해도 충돌하지 않는다
    (과거 스케줄과 현재 스케줄이 겹치는 문제 방지)."""
    deps = [v for v in ship.get('Departure Ports', {}).values()
            if v and v != '-' and ISO_RE.match(v)]
    if deps:
        anchor = min(deps)
    else:
        arrs = [v for v in ship.get('Arrival Ports', {}).values()
                if v and v != '-' and ISO_RE.match(v)]
        anchor = min(arrs) if arrs else 'NA'
    return f"{anchor}_{ship.get('Ship Name','')}_{ship.get('Voyage','')}"


def normalize_ship(ship, base):
    """선박 dict의 모든 날짜를 ISO로 변환하고 고유 id를 부여한 새 dict 반환."""
    dep = {p: to_iso(v, base) for p, v in ship.get('Departure Ports', {}).items()}
    arr = {p: to_iso(v, base) for p, v in ship.get('Arrival Ports', {}).items()}
    ordered = {
        'Company': ship.get('Company', ''),
        'Ship Name': ship.get('Ship Name', ''),
        'Voyage': ship.get('Voyage', ''),
        'Departure Ports': dep,
        'Arrival Ports': arr,
    }
    ordered['id'] = make_id(ordered)
    # id를 보기 좋게 앞쪽(보야드 다음)에 배치
    return {
        'Company': ordered['Company'],
        'Ship Name': ordered['Ship Name'],
        'Voyage': ordered['Voyage'],
        'id': ordered['id'],
        'Departure Ports': dep,
        'Arrival Ports': arr,
    }


def parse_date_from_str(date_str, base=None):
    """날짜 문자열을 datetime으로 변환. 신규 'YYYY-MM-DD'와 레거시 'Apr21' 모두 지원."""
    if not date_str or date_str == '-':
        return None
    if ISO_RE.match(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            return None
    iso = to_iso(date_str, base or get_kst_now())
    if ISO_RE.match(iso):
        try:
            return datetime.strptime(iso, '%Y-%m-%d')
        except ValueError:
            return None
    return None

def get_latest_departure_date(ship):
    """선박 데이터에서 가장 늦은 출발일을 반환."""
    latest = None
    for port, date_str in ship.get('Departure Ports', {}).items():
        d = parse_date_from_str(date_str)
        if d and (latest is None or d > latest):
            latest = d
    return latest

def ship_key(item):
    """항차 식별 키(회사|선명|보야드). 보드에 아직 떠있는지 판단·변경요약용."""
    return f"{item.get('Company','')}¦{item.get('Ship Name','')}¦{item.get('Voyage','')}"

def voyage_uid(item):
    """저장/아카이브 중복 판별용 고유 ID(출발일 포함)."""
    return item.get('id') or make_id(item)

def update_archive(existing_data, current_data, archive_file):
    """기존 데이터 중 출발일이 모두 지난 스케줄을 아카이브에 추가.

    Args:
        existing_data: 갱신 전 현재 JSON 데이터 (list or None)
        current_data: 새로 크롤링한 데이터 (list)
        archive_file: 아카이브 JSON 파일 경로
    """
    now = get_kst_now()

    # 아카이브 파일 로드
    archive_data = []
    if os.path.exists(archive_file):
        with open(archive_file, 'r', encoding='utf-8') as f:
            archive_data = json.load(f)
    # 레거시 항목 보강: id가 없으면 생성
    for item in archive_data:
        if 'id' not in item:
            item['id'] = make_id(item)

    # 중복 판별은 출발일 포함 고유 id로, '아직 활성인지'는 항차 식별 키로 판단
    archive_ids = {voyage_uid(item) for item in archive_data}
    active_identities = {ship_key(item) for item in current_data}

    added_count = 0

    def maybe_archive(ship):
        nonlocal added_count
        uid = voyage_uid(ship)
        if uid in archive_ids:
            return
        latest_dep = get_latest_departure_date(ship)
        if latest_dep and now > latest_dep:
            archive_data.append(ship)
            archive_ids.add(uid)
            added_count += 1

    # 아카이브 대상: 기존 데이터에는 있었지만 보드에서 사라진 항차 중 출발일이 지난 것
    if existing_data:
        for ship in existing_data:
            # 같은 항차가 아직 보드에 떠있으면 활성 상태이므로 스킵
            if ship_key(ship) in active_identities:
                continue
            maybe_archive(ship)

    # 추가로: 새 데이터에서도 출발일이 모두 지난 것은 아카이브에 추가
    # (갱신 후에도 사라지지 않도록)
    for ship in current_data:
        maybe_archive(ship)

    # 아카이브 저장
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)

    print(f"아카이브 업데이트: {added_count}개 스케줄 추가 (총 {len(archive_data)}개 보존)")

# 크롤링 설정 정의
SCRAPE_CONFIGS = [
    {
        "name": "ASIA",
        "url": "https://autocj.co.jp/japan_shipping?dest=8",
        "history_file": "shipping_update_east_asia.json",
        "archive_file": "shipping_archive_east_asia.json",
        "departure_ports": ["Yokohama", "Kawasaki", "Kisarazu", "Nagoya", "Kobe", "Osaka", "Hakata", "Hibikinada", "Kanda", "Hitachinaka"],
        "arrival_ports": ["Hong Kong", "Laem Chabang", "Hambantota", "Chittagong", "Mongla", "Subic"]
    },
    {
        "name": "AFRICA",
        "url": "https://autocj.co.jp/japan_shipping?dest=2",
        "history_file": "shipping_update_asia_africa.json",
        "archive_file": "shipping_archive_asia_africa.json",
        "departure_ports": ["Yokohama", "Kawasaki", "Kisarazu", "Nagoya", "Kobe", "Osaka", "Hakata", "Hibikinada", "Kanda", "Nakanoseki", "Hitachinaka"],
        "arrival_ports": ["Jebel Ali", "Karachi", "Port Louis", "Durban", "Dar", "Mombasa", "Maput"]
    }
]

def scrape_page(config):
    """단일 페이지 크롤링 및 업데이트.

    Args:
        config (dict): 크롤링 설정 (url, history_file, departure_ports, arrival_ports, name)

    Returns:
        tuple: (변경 여부 bool, 변경 요약 문자열)
    """
    url = config["url"]
    history_file = config["history_file"]
    archive_file = config["archive_file"]
    departure_ports = config["departure_ports"]
    arrival_ports = config["arrival_ports"]
    route_name = config["name"]

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    print(f"\n[{get_kst_now()}] {route_name} 크롤링을 시작합니다...")
    print(f"URL: {url}")

    try:
        # 1. 웹사이트 데이터 가져오기
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("1. 웹사이트 접속 성공")

        # 2. BeautifulSoup으로 HTML 파싱 (html5lib로 내결함성 강화)
        soup = BeautifulSoup(response.text, 'html5lib')

        # 3. 데이터 테이블 찾기: div.ship_c > table.main
        ship_div = soup.find('div', class_='ship_c')
        if not ship_div:
            print("에러: div.ship_c를 찾을 수 없습니다.")
            return

        data_table = ship_div.find('table', class_='main')
        if not data_table:
            print("에러: table.main을 찾을 수 없습니다.")
            return

        print("2. 데이터 테이블을 찾았습니다.")

        # 4. 모든 행 추출 (tbody 하위 tr.row 우선, 없으면 tr 전체)
        rows = data_table.select('tbody > tr.row')
        if not rows:
            rows = data_table.select('tbody > tr')
        print(f"3. {len(rows)}개의 행을 찾았습니다.")

        # 5. 데이터 파싱
        current_data = []

        for row in rows:
            # td 셀 추출 (html5lib 파서로 정확한 셀 분리)
            cells = row.find_all('td')

            # 최소 셀 개수 확인 (3 + 출발항 + 도착항)
            min_cells = 3 + len(departure_ports) + len(arrival_ports)
            if len(cells) < min_cells:
                continue

            # 기본 정보 추출 (인덱스 0, 1, 2) - 첫 td만 회사명
            company = cells[0].get_text(strip=True)
            ship_name = cells[1].get_text(strip=True)
            voyage = cells[2].get_text(strip=True)

            # 출발항 정보 추출
            departure_dict = {}
            for i, port_name in enumerate(departure_ports):
                cell_index = 3 + i
                cell_value = cells[cell_index].get_text(strip=True).replace('\n', '').replace(' ', '')
                departure_dict[port_name] = cell_value if cell_value else "-"

            # 도착항 정보 추출
            arrival_dict = {}
            for i, port_name in enumerate(arrival_ports):
                cell_index = 3 + len(departure_ports) + i
                cell_value = cells[cell_index].get_text(strip=True).replace('\n', '').replace(' ', '')
                arrival_dict[port_name] = cell_value if cell_value else "-"

            ship_data = {
                "Company": company,
                "Ship Name": ship_name,
                "Voyage": voyage,
                "Departure Ports": departure_dict,
                "Arrival Ports": arrival_dict
            }

            current_data.append(ship_data)

        print(f"4. 데이터 추출 완료 ({len(current_data)}개 선박 정보)")

        # 4-1. 크롤링 시점 기준으로 연도를 확정해 ISO('YYYY-MM-DD')로 변환 + 고유 id 부여
        now = get_kst_now()
        current_data = [normalize_ship(s, now) for s in current_data]

        # 5. 기존 데이터 불러오기
        existing_data = None
        if os.path.exists(history_file):
            with open(history_file, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            # 기존 파일도 동일 포맷으로 정규화하여 비교(이미 ISO면 idempotent)
            existing_data = [normalize_ship(s, now) for s in existing_data]
            print(f"5. 기존 파일 '{history_file}'을 불러왔습니다.")
        else:
            print("5. 기존 파일이 없습니다. 새로 생성합니다.")

        # 6. 변경 사항 비교
        if existing_data is not None and existing_data == current_data:
            print("결과: 기존 데이터와 동일합니다. 변경 사항이 없어 저장하지 않습니다.")
            # 변경이 없더라도 아카이브는 업데이트 (출발일이 지난 스케줄 보존)
            print("아카이브를 확인합니다...")
            update_archive(existing_data, current_data, archive_file)
            return False, None

        # 변경 요약 생성
        if existing_data is not None:
            change_summary = summarize_changes(existing_data, current_data)
        else:
            change_summary = summarize_changes(None, current_data)

        # 7. 아카이브 업데이트 (출발일이 지난 스케줄 보존)
        print("6. 아카이브를 업데이트합니다...")
        update_archive(existing_data, current_data, archive_file)

        # 8. 데이터 저장 (덮어쓰기)
        print("7. 변경 사항 확인! 새 데이터를 저장합니다.")
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)

        full_path = os.path.abspath(history_file)
        print(f"최종 결과: 파일 저장 완료! 위치: {full_path}")
        return True, change_summary

    except Exception as e:
        print(f"실행 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def scrape_and_update():
    """모든 설정된 페이지를 크롤링하고 업데이트."""
    print(f"====== 크롤링 시작: {get_kst_now().strftime('%Y-%m-%d %H:%M:%S')} ======")

    results = []
    combined_summaries = []
    for config in SCRAPE_CONFIGS:
        changed, summary = scrape_page(config)
        results.append({"route": config["name"], "changed": changed})
        if changed and summary:
            combined_summaries.append(f"[{config['name']}] 라우트 변경 사항:\n{summary}")

    print(f"\n====== 크롤링 완료: {get_kst_now().strftime('%Y-%m-%d %H:%M:%S')} ======")
    print("\n결과 요약:")
    for result in results:
        status = "변경됨" if result["changed"] else "변경 없음"
        print(f"  - {result['route']}: {status}")

    if combined_summaries:
        print("\n변경 사항을 모아서 이메일 알림을 전송합니다...")
        full_summary = ""
        for i, summary in enumerate(combined_summaries):
            if i > 0:
                full_summary += "\n\n" + "="*40 + "\n\n"
            full_summary += summary

        # 통합 알림을 위한 라우트 이름 조합 (예: ASIA & AFRICA)
        changed_routes = [res['route'] for res in results if res['changed']]
        combined_route_name = " & ".join(changed_routes)

        send_notification_email(full_summary, route_name=combined_route_name)

def _legacy_to_iso(date_str, base_year):
    """레거시 'Apr21'을 고정 연도(base_year) 기준 ISO로 변환. 이미 ISO/'-'이면 그대로."""
    if not date_str or date_str == '-':
        return '-'
    if ISO_RE.match(date_str):
        return date_str
    m = MONDD_RE.match(date_str)
    if not m or m.group(1) not in MONTHS:
        return date_str
    mon_idx = MONTHS.index(m.group(1))
    day = int(m.group(2))
    try:
        return datetime(base_year, mon_idx + 1, day).strftime('%Y-%m-%d')
    except ValueError:
        return date_str


def migrate_legacy_files(base_year=2026):
    """기존 update/archive JSON(연도 없는 'Apr21')을 ISO + id 포맷으로 1회 변환.

    현재 누적된 과거 데이터는 모두 단일 연도(2026)에 속하므로 base_year를 일괄 적용한다.
    id(출발일-선명-보야드) 기준으로 중복도 함께 제거한다. 연말→연초를 넘나드는 항차의
    연도 처리는 이후 실제 크롤링 시 resolve_year가 담당한다(아카이브 적재 시점에 확정)."""
    files = ([c['history_file'] for c in SCRAPE_CONFIGS]
             + [c['archive_file'] for c in SCRAPE_CONFIGS])
    for path in files:
        if not os.path.exists(path):
            print(f"건너뜀(파일 없음): {path}")
            continue
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        migrated = []
        seen = set()
        for ship in data:
            dep = {p: _legacy_to_iso(v, base_year)
                   for p, v in ship.get('Departure Ports', {}).items()}
            arr = {p: _legacy_to_iso(v, base_year)
                   for p, v in ship.get('Arrival Ports', {}).items()}
            ordered = {
                'Company': ship.get('Company', ''),
                'Ship Name': ship.get('Ship Name', ''),
                'Voyage': ship.get('Voyage', ''),
                'Departure Ports': dep,
                'Arrival Ports': arr,
            }
            uid = make_id(ordered)
            if uid in seen:
                continue  # [출발일-선명-보야드] 중복 제거
            seen.add(uid)
            migrated.append({
                'Company': ordered['Company'],
                'Ship Name': ordered['Ship Name'],
                'Voyage': ordered['Voyage'],
                'id': uid,
                'Departure Ports': dep,
                'Arrival Ports': arr,
            })

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(migrated, f, ensure_ascii=False, indent=2)
        removed = len(data) - len(migrated)
        print(f"마이그레이션 완료: {path} → {len(migrated)}개 (중복 {removed}개 제거)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("테스트 모드로 실행합니다...")
        send_test_email()
    elif len(sys.argv) > 1 and sys.argv[1] == "--migrate":
        print("레거시 JSON 마이그레이션을 실행합니다...")
        migrate_legacy_files()
    else:
        scrape_and_update()
