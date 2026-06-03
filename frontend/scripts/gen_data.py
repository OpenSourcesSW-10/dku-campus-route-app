#!/usr/bin/env python3
"""
받은 원본 엑셀(scripts/source/*.xlsx)을 읽어 앱에서 쓰는 정규화 JSON으로 변환한다.
출력: src/data/dku-data.json
좌표 캔버스 기준: 1000 x 707 (제공된 PNG와 1:1 정렬됨)

사용: python3 scripts/gen_data.py
원본 좌표가 갱신되면 source 교체 후 재실행하면 데이터가 다시 생성된다.
"""
import zipfile, re, html, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'source')
OUT = os.path.join(HERE, '..', 'src', 'data', 'dku-data.json')
CANVAS_W, CANVAS_H = 1000, 707


def read_sheet(path):
    z = zipfile.ZipFile(path)
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        raw = z.read('xl/sharedStrings.xml').decode('utf-8')
        for si in re.findall(r'<(?:x:)?si>(.*?)</(?:x:)?si>', raw, re.S):
            ss.append(html.unescape(''.join(re.findall(r'<(?:x:)?t[^>]*>(.*?)</(?:x:)?t>', si, re.S))))
    sheet = sorted(n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml', n))[0]
    raw = z.read(sheet).decode('utf-8')
    rows = []
    for r in re.findall(r'<(?:x:)?row\b[^>]*>(.*?)</(?:x:)?row>', raw, re.S):
        line = {}
        for m in re.finditer(r'<(?:x:)?c\b([^>]*?)(?:/>|>(.*?)</(?:x:)?c>)', r, re.S):
            attrs, inner = m.group(1), (m.group(2) or '')
            ref = re.search(r'r="([A-Z]+)\d+"', attrs)
            typ = re.search(r't="([^"]+)"', attrs)
            v = re.search(r'<(?:x:)?v>(.*?)</(?:x:)?v>', inner, re.S)
            val = html.unescape(v.group(1)) if v else ''
            if typ and typ.group(1) == 's' and val != '':
                val = ss[int(val)]
            if ref:
                line[ref.group(1)] = val
        rows.append(line)
    return rows


def as_table(rows):
    """헤더 행을 찾아 dict 리스트로 변환 (빈 셀/시작열 무관)."""
    header = None
    out = []
    for r in rows:
        vals = [v for v in r.values() if v != '']
        if header is None:
            if len(vals) >= 2:
                # 컬럼레터 -> 헤더명 매핑
                header = {col: name for col, name in r.items() if name != ''}
            continue
        rec = {header[col]: r.get(col, '') for col in header}
        if any(v != '' for v in rec.values()):
            out.append(rec)
    return out


def f(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ---- buildings ----
bm = as_table(read_sheet(os.path.join(SRC, 'Building_Master.xlsx')))
buildings = []
for r in bm:
    buildings.append({
        'id': r['building_id'],
        'code': r['building_code'],
        'name': r['building_name'],
        'lat': f(r['latitude']),
        'lng': f(r['longitude']),
        'category': r.get('category', ''),
        'floorsAbove': int(f(r.get('floors_above', 0)) or 0),
        'floorsBelow': int(f(r.get('floors_below', 0)) or 0),
        'hasIndoorMap': str(r.get('has_indoor_map', '')).strip() in ('1', '1.0', 'TRUE', 'True'),
    })

# ---- aliases ----
al = as_table(read_sheet(os.path.join(SRC, 'Building_aliases.xlsx')))
aliases = []
for r in al:
    bid = r.get('building_id', '')
    alias = r.get('alias', '')
    if bid and alias:
        aliases.append({'alias': alias.strip(), 'buildingId': bid.strip()})

# ---- room positions (DKU 체계) ----
rp = as_table(read_sheet(os.path.join(SRC, 'rooms_positions.xlsx')))
pos_by_room = {}
for r in rp:
    rid = r.get('room_id', '')
    x, y, w, h = f(r.get('x')), f(r.get('y')), f(r.get('width')), f(r.get('height'))
    if rid and None not in (x, y, w, h):
        poly = r.get('polygon_points', '') or ''
        points = []
        if poly and poly != 'NULL':
            for pt in poly.split(';'):
                xy = pt.split(',')
                if len(xy) == 2:
                    px, py = f(xy[0]), f(xy[1])
                    if px is not None and py is not None:
                        points.append([px, py])
        pos_by_room[rid] = {
            'x': x, 'y': y, 'width': w, 'height': h,
            'cx': round(x + w / 2, 1), 'cy': round(y + h / 2, 1),
            'polygon': points or None,
        }

# ---- rooms (DKU 체계) ----
rm = as_table(read_sheet(os.path.join(SRC, 'rooms_master.xlsx')))
bname = {b['id']: b['name'] for b in buildings}
# 건물별 대표 약칭 (priority 무시, 첫 한글 약칭 선호)
short_alias = {}
for a in aliases:
    short_alias.setdefault(a['buildingId'], a['alias'])

rooms = []
for r in rm:
    rid = r.get('room_id', '')
    bid = r.get('building_id', '')
    if not rid or not bid:
        continue
    num = r.get('room_code', '')
    label = r.get('floor_label', '')
    name = r.get('room_name', '') or ''
    if name in ('unknown', 'NULL'):
        name = ''
    rooms.append({
        'id': rid,
        'buildingId': bid,
        'floor': int(f(r.get('floor_number', 0)) or 0),
        'floorLabel': label,
        'number': num,
        'name': name,
        'type': r.get('room_type', ''),
        'displayName': f"{bname.get(bid, bid)} {num}호" + (f" ({name})" if name else ''),
        'pos': pos_by_room.get(rid),
    })

# ---- indoor maps (층 목록 + 이미지 경로) ----
PNG = {
    'DKU_ICT': ('ICT', {-1: 'ICT_B1-1.png', 1: 'ICT_1Fa-1.png', 2: 'ICT_2Fa-1.png',
                        3: 'ICT_3Fa-1.png', 4: 'ICT_4Fa-1.png', 5: 'ICT_5Fa-1.png'}),
    'DKU_LIB': ('LIB', {1: 'LIB_1Fa-1.png', 2: 'LIB_2Fa-1.png', 3: 'LIB_3Fa-1.png',
                        4: 'LIB_4Fa-1.png', 5: 'LIB_5Fa-1.png', 6: 'LIB_6Fa-1.png'}),
}
indoor_maps = []
for bid, (folder, files) in PNG.items():
    floors = sorted({rm2['floor'] for rm2 in rooms if rm2['buildingId'] == bid})
    for fl in floors:
        if fl not in files:
            continue
        lab = next((rm2['floorLabel'] for rm2 in rooms if rm2['buildingId'] == bid and rm2['floor'] == fl), str(fl))
        indoor_maps.append({
            'buildingId': bid,
            'floor': fl,
            'floorLabel': lab,
            'image': f"/floorplans/{folder}/{files[fl]}",
            'canvasWidth': CANVAS_W,
            'canvasHeight': CANVAS_H,
        })

data = {
    'canvas': {'width': CANVAS_W, 'height': CANVAS_H},
    'buildings': buildings,
    'aliases': aliases,
    'rooms': rooms,
    'indoorMaps': indoor_maps,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as fp:
    json.dump(data, fp, ensure_ascii=False, indent=2)

withpos = sum(1 for r in rooms if r['pos'])
print(f"buildings={len(buildings)} aliases={len(aliases)} rooms={len(rooms)} (좌표 {withpos}) indoorMaps={len(indoor_maps)}")
print("wrote", os.path.relpath(OUT, os.path.join(HERE, '..')))
