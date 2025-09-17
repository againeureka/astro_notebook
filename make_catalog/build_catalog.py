# build_catalog.py
# Python 3.9+

import json
import re
import argparse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ---------------- 한국어 이름 매핑(필요 시 확장) ----------------
KO_MAP = {
    # Messier(대표 예시)
    "Andromeda Galaxy": "안드로메다 은하",
    "Orion Nebula": "오리온 대성운",
    "Pleiades": "플레이아데스 성단",
    "Lagoon Nebula": "라군 성운",
    "Ring Nebula": "링 성운",
    "Dumbbell Nebula": "덤벨 성운",
    "Hercules Globular Cluster": "헤라클레스 구상성단",
    "Omega Nebula": "오메가 성운",
    "Trifid Nebula": "트리피드 성운",
    "Sombrero Galaxy": "솜브레로 은하",
    # 밝은 별(일부)
    "Sirius": "시리우스",
    "Canopus": "카노푸스",
    "Arcturus": "아크투루스",
    "Vega": "베가",
    "Capella": "카펠라",
    "Rigel": "리겔",
    "Procyon": "프로키온",
    "Achernar": "아케르나르",
    "Betelgeuse": "베텔지우스",
    "Altair": "알타이르",
    "Deneb": "데네브",
    "Polaris": "폴라리스",
}

# ---------------- 태양계 행성(항상 포함; RA/Dec는 시각 의존이므로 null) ----------------
SOLAR_SYSTEM = [
    ("Mercury", "수성"), ("Venus", "금성"), ("Earth", "지구"), ("Mars", "화성"),
    ("Jupiter", "목성"), ("Saturn", "토성"), ("Uranus", "천왕성"), ("Neptune", "해왕성"),
    ("Pluto", "명왕성"),
    ("Ganymede", "가니메데"), ("Titan", "타이탄"),
]

# ---------------- 유틸 ----------------
def norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    s = (s.replace("−", "-")
           .replace("–", "-")
           .replace("—", "-")
           .replace("º", "°")
           .replace("’", "'")
           .replace("″", '"'))
    return s

def float_or_none(x: Any) -> Optional[float]:
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(str(x).replace("+", ""))
    except Exception:
        return None

def hms_to_str(h: int, m: int, s: float) -> str:
    return f"{h:02d}:{m:02d}:{s:05.2f}"

def dms_to_str(sign: int, d: int, m: int, s: float) -> str:
    return f"{'+' if sign >= 0 else '-'}{d:02d}:{m:02d}:{s:05.2f}"

def first(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and v.strip() == "":
            continue
        return v
    return None

# ---------------- simpleMessier 실제 포맷 파서 ----------------
# 예:
# { "name": "M1, Crab Nebula.", "coordinates": "RA 05h 34.5m, LD. +22º 01’", "magnitude": 8.4 }
MESSIER_ID_RE = re.compile(r"\bM\s*([0-9]{1,3})\b", re.IGNORECASE)
RA_RE = re.compile(
    r"RA\s*([0-9]{1,2})h\s*([0-9]{1,2}(?:\.[0-9]+)?)m(?:\s*([0-9]{1,2}(?:\.[0-9]+)?)s)?",
    re.IGNORECASE
)
DEC_RE = re.compile(
    r"(?:Dec|LD\.?)\s*([+\-−–]?)\s*([0-9]{1,2})[°º]\s*([0-9]{1,2})['’]?(?:\s*([0-9]{1,2}(?:\.[0-9]+)?)\"?)?",
    re.IGNORECASE
)

def parse_messier_row(row: Dict[str, Any]) -> Dict[str, Any]:
    raw_name = norm_str(row.get("name"))
    coords = norm_str(row.get("coordinates"))
    mag = float_or_none(row.get("magnitude"))

    # id
    mid = "M?"
    m = MESSIER_ID_RE.search(raw_name or "") if raw_name else None
    if m:
        mid = f"M{int(m.group(1))}"

    # name_en: "M1, Crab Nebula." -> "Crab Nebula"
    name_en = None
    if raw_name:
        parts = [p.strip() for p in raw_name.split(",")]
        if parts and parts[0].upper().startswith("M"):
            name_en = parts[1] if len(parts) > 1 else None
        if name_en:
            name_en = name_en.rstrip(".")
        if not name_en:
            name_en = re.sub(MESSIER_ID_RE, "", raw_name).strip().strip(",").strip()
            name_en = name_en.rstrip(".") if name_en else None
        if not name_en:
            name_en = mid

    ra_str, dec_str = None, None
    if coords:
        c = coords.replace("LD.", "Dec").replace("ld.", "Dec")
        c = c.replace("–", "-").replace("−", "-").replace("º", "°")
        ra_match = RA_RE.search(c)
        if ra_match:
            hh = int(ra_match.group(1))
            mm = float(ra_match.group(2))
            ss = float(ra_match.group(3) or 0.0)
            mm_i = int(mm)
            ss += (mm - mm_i) * 60.0
            ra_str = hms_to_str(hh, mm_i, ss)
        dec_match = DEC_RE.search(c)
        if dec_match:
            sgn = -1 if (dec_match.group(1) or "").startswith("-") else 1
            dd = int(dec_match.group(2))
            dm = int(dec_match.group(3))
            ds = float(dec_match.group(4) or 0.0)
            dec_str = dms_to_str(sgn, dd, dm, ds)

    return {
        "id": mid,
        "catalog": "Messier",
        "name_en": name_en,
        "name_kr": KO_MAP.get(name_en) if name_en else 'na',
        "ra": ra_str,
        "dec": dec_str,
        "magnitude": mag,
        "type": None,
        "constellation": None,
    }

def normalize_messier_simple(list_data: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for row in list_data:
        try:
            out.append(parse_messier_row(row))
        except Exception:
            raw_name = norm_str(row.get("name"))
            m = MESSIER_ID_RE.search(raw_name or "") if raw_name else None
            mid = f"M{int(m.group(1))}" if m else "M?"
            out.append({
                "id": mid,
                "catalog": "Messier",
                "name_en": raw_name,
                "name_kr": 'na',
                "ra": None,
                "dec": None,
                "magnitude": float_or_none(row.get("magnitude")),
                "type": None,
                "constellation": None,
            })
    return out

# ---------------- BSC5P(제공해주신 스키마 전용) ----------------
# 예시 필드:
# hoursRaJ2000, minutesRaJ2000, secondsRaJ2000,
# signDecJ2000, degreesDecJ2000, minutesDecJ2000, secondsDecJ2000,
# visualMagnitude, spectralType, hdId, saoId, bayerAndOrFlamsteed ...
def bsc5p_build_hms(d: Dict[str, Any]) -> Optional[str]:
    try:
        h = int(d.get("hoursRaJ2000"))
        m = int(d.get("minutesRaJ2000"))
        s = float(d.get("secondsRaJ2000"))
        return hms_to_str(h, m, s)
    except Exception:
        return None

def bsc5p_build_dms(d: Dict[str, Any]) -> Optional[str]:
    try:
        sign = 1 if (d.get("signDecJ2000") or "+").strip() != "-" else -1
        deg = int(d.get("degreesDecJ2000"))
        minu = int(d.get("minutesDecJ2000"))
        sec = float(d.get("secondsDecJ2000"))
        return dms_to_str(sign, deg, minu, sec)
    except Exception:
        return None

def normalize_bsc5p_known_schema(stars: Iterable[Dict[str, Any]], mag_threshold: Optional[float]) -> List[Dict[str, Any]]:
    out = []
    for s in stars:
        # 등급
        magnitude = float_or_none(s.get("visualMagnitude"))
        if mag_threshold is not None and magnitude is not None and magnitude > mag_threshold:
            continue

        # ID: 우선순위 (Bayer/Flamsteed) > HD > SAO
        bayer = norm_str(s.get("bayerAndOrFlamsteed"))
        hd = norm_str(s.get("hdId"))
        sao = norm_str(s.get("saoId"))
        sid = first(bayer, (f"HD {hd}" if hd else None), (f"SAO {sao}" if sao else None), norm_str(s.get("dmId")), norm_str(s.get("adsId"))) or f"line:{s.get('lineNumber','?')}"

        # 이름(영문): 보통 공식 고유명은 파일에 잘 없으므로 Bayer/Flamsteed를 name_en으로 사용
        name_en = bayer or sid

        # 좌표(분해)
        ra_str = bsc5p_build_hms(s)
        dec_str = bsc5p_build_dms(s)

        spectral = norm_str(s.get("spectralType"))
        constel = None  # 제공 스니펫엔 별자리 코드가 없어서 None

        out.append({
            "id": sid,
            "catalog": "BrightStar",
            "name_en": name_en,
            "name_kr": KO_MAP.get(name_en, 'na'),
            "ra": ra_str,
            "dec": dec_str,
            "magnitude": magnitude,
            "spectralType": spectral,
            "constellation": constel,
        })
    return out

# ---------------- 태양계 기본 목록 생성 ----------------
def build_solar_bodies() -> List[Dict[str, Any]]:
    out = []
    for en, kr in SOLAR_SYSTEM:
        out.append({
            "id": f"planet:{en.lower()}",
            "catalog": "SolarSystem",
            "name_en": en,
            "name_kr": kr,
            "ra": None,
            "dec": None,
            "type": "Planet" if en not in ("Ganymede", "Titan", "Pluto") else ("Moon" if en in ("Ganymede", "Titan") else "DwarfPlanet"),
            "constellation": None,
        })
    return out

# ---------------- 메인 ----------------
def main():
    ap = argparse.ArgumentParser(description="simpleMessier(master_data.json) + BSC5P(제공 스키마) → 한/영 병기 통합 카탈로그")
    ap.add_argument("--messier", required=True, help="simpleMessier의 master_data.json")
    ap.add_argument("--bsc5p", required=True, help="제공하신 스키마의 bsc5p.json")
    ap.add_argument("--out", default="catalog_ko_en.json", help="출력 파일")
    ap.add_argument("--bsc5p-mag", type=float, default=6.5, help="BSC5P 임계 등급(이하만 포함). 기본 6.5")
    args = ap.parse_args()

    with Path(args.messier).open("r", encoding="utf-8") as f:
        messier_raw = json.load(f)
    with Path(args.bsc5p).open("r", encoding="utf-8") as f:
        bsc5p_raw = json.load(f)

    # 리스트 가정, 방어 처리
    messier_iter = messier_raw if isinstance(messier_raw, list) else messier_raw.get("data", [])
    bsc5p_iter = bsc5p_raw if isinstance(bsc5p_raw, list) else bsc5p_raw.get("data", [])

    messier = normalize_messier_simple(messier_iter)             # 100% 포함
    bright  = normalize_bsc5p_known_schema(bsc5p_iter, args.bsc5p_mag)
    solar   = build_solar_bodies()

    # 병합(id 기준 빈칸 보완)
    def fill_missing(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged = base.copy()
        for k, v in patch.items():
            if merged.get(k) in (None, "") and v not in (None, ""):
                merged[k] = v
        return merged

    by_id: Dict[str, Dict[str, Any]] = {}
    for item in messier + bright + solar:
        i = item.get("id")
        if not i:
            continue
        if i in by_id:
            by_id[i] = fill_missing(by_id[i], item)
        else:
            by_id[i] = item

    out = list(by_id.values())

    # 정렬: catalog → magnitude(오름) → name_en
    def sort_key(o):
        cat = o.get("catalog") or ""
        mag = o.get("magnitude")
        mag = 99.0 if mag is None else mag
        name = o.get("name_en") or ""
        return (cat, mag, name)

    out.sort(key=sort_key)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"✔ Done. Wrote {len(out)} objects → {args.out}")

if __name__ == "__main__":
    main()