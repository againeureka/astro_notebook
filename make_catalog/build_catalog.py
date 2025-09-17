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
    "Rigel Kentaurus": "리겔 케타우루스",
    "Aldebaran": "알데바란",
    "Antares": "안타레스",
    "Pollux": "폴룩스",
    "Fomalhaut": "포말하우트",
    "Mimosa": "미모사",
    "Regulus": "레굴루스",
    "Bellatrix": "벨라트릭스",
    "Elnath": "엘나스",
    "Alnilam": "알닐람",
    "Alnair": "알나이르",
    "Alioth": "알리오스",
    "Mirfak": "미르팍",
    "Alkaid": "알카이드",
    "Peacock": "피콕, 공작",
    "Mirzam": "미르잠",
}

# ---------------- 태양계 행성(항상 포함; RA/Dec는 시각 의존이므로 null) ----------------
SOLAR_SYSTEM = [
    ("Mercury", "수성"), ("Venus", "금성"), ("Earth", "지구"), ("Mars", "화성"),
    ("Jupiter", "목성"), ("Saturn", "토성"), ("Uranus", "천왕성"), ("Neptune", "해왕성"),
    ("Pluto", "명왕성"), ("Moon", "달"),
    ("Ganymede", "가니메데"), ("Io", "이오"), ("Callisto", "칼리스토"), ("Europa", "유로파"),
    ("Titan", "타이탄"), 
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
           .replace("“", "\"")
           .replace("”", "\"")
           .replace("″", '"'))
    return s

def float_or_none(x: Any) -> Optional[float]:
    try:
        if x is None or str(x).strip() == "" or str(x).lower() == "none":
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

# ---------------- 간단 영→한 발음 변환 ----------------
# --- hangulize 기반 영→한 변환 ---
def eng_to_hangul(name: str) -> str:
    """
    영어 이름을 한국어 표기로 변환.
    - hangulize가 설치되어 있지 않거나 변환 실패 시 원문을 반환(안전).
    - 입력이 빈 값/None이면 빈 문자열 반환.
    """
    if not name:
        return ""
    try:
        from hangulize import hangulize
        from hangulize.langs.eng import English
    except Exception:
        # 라이브러리 미설치 등: 원문 반환
        return str(name)

    # 전처리: 공백/하이픈 정리 (필요 시 규칙 확장)
    txt = str(name).strip()
    if not txt:
        return ""

    # hangulize는 영문 고유명에 강함. 복합명칭은 토큰 단위로 처리 후 합침.
    # (예: "Sirius A" -> ["Sirius", "A"] 각각 변환 후 합쳐서 반환)
    tokens = [t for t in re.split(r"\s*[-\s]\s*", txt) if t]
    out = []
    for t in tokens:
        try:
            ko = hangulize(t, English)
            out.append(ko)
        except Exception:
            # 토큰 단위 실패 시 해당 토큰은 원문 유지
            out.append(t)
    return "".join(out)


# 아주 간단한 규칙 기반 변환입니다(완벽 X). KO_MAP이 우선.
def eng_to_hangul_simple(name: str) -> str:
    if not name:
        return ""
    # 특수기호 제거/토큰화
    txt = re.sub(r"[^A-Za-z0-9\s\-]", " ", name)
    tokens = [t for t in re.split(r"[\s\-]+", txt) if t]
    # 간단 매핑
    repl = [
        (r"ph", "프"), (r"ch", "치"), (r"sh", "시"), (r"th", "스"), (r"gh", "그"),
        (r"ck", "크"), (r"qu", "쿠"), (r"x", "크스"), (r"ce", "스"), (r"ci", "시"),
        (r"ge", "지"), (r"gi", "지"),
    ]
    vowel = {
        "a":"아","e":"에","i":"이","o":"오","u":"우","y":"이",
        "aa":"아","ee":"이","oo":"우","ai":"아이","au":"아우","ei":"에이","ou":"오우",
    }
    cons = {
        "b":"브","c":"크","d":"드","f":"프","g":"그","h":"흐","j":"지","k":"크","l":"르",
        "m":"므","n":"느","p":"프","q":"쿠","r":"르","s":"스","t":"트","v":"브","w":"우",
        "z":"즈",
    }
    out_words = []
    for w in tokens:
        lw = w.lower()
        # 규칙 치환
        for a, b in repl:
            lw = re.sub(a, b, lw)
        # 간단 조합: 모음/자음 순차 치환
        syll = []
        i = 0
        while i < len(lw):
            # 이중 모음 우선
            if i+1 < len(lw) and lw[i:i+2] in vowel:
                syll.append(vowel[lw[i:i+2]])
                i += 2
                continue
            ch = lw[i]
            if ch in vowel:
                syll.append(vowel[ch])
            elif ch.isalpha():
                syll.append(cons.get(ch, ch))
            else:
                syll.append(ch)
            i += 1
        out_words.append("".join(syll))
    return "".join(out_words)

# ---------------- Messier (수정된 포맷) ----------------
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
    name_en_field = norm_str(row.get("name_en")) or None
    name_kr_field = norm_str(row.get("name_kr")) or None
    coords = norm_str(row.get("coordinates"))
    mag = float_or_none(row.get("magnitude"))

    mid = "M?"
    m = MESSIER_ID_RE.search(raw_name or "")
    if m:
        mid = f"M{int(m.group(1))}"

    name_en = name_en_field
    if not name_en:
        if raw_name:
            parts = [p.strip() for p in raw_name.split(",")]
            if parts and parts[0].upper().startswith("M"):
                name_en = parts[1] if len(parts) > 1 else None
            if name_en:
                name_en = name_en.rstrip(".")
        if not name_en:
            name_en = mid

    # name_kr: 필드 우선 -> KO_MAP -> 발음 변환
    name_kr = name_kr_field or KO_MAP.get(name_en) or eng_to_hangul(name_en)

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
        "name_kr": name_kr,
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
            name_en = norm_str(row.get("name_en")) or raw_name or mid
            out.append({
                "id": mid,
                "catalog": "Messier",
                "name_en": name_en,
                "name_kr": norm_str(row.get("name_kr")) or KO_MAP.get(name_en) or eng_to_hangul(name_en),
                "ra": None,
                "dec": None,
                "magnitude": float_or_none(row.get("magnitude")),
                "type": None,
                "constellation": None,
            })
    return out

# ---------------- BSC5P(제공 스키마 + namesAlt 지원) ----------------
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

def pick_common_name(names_alt: List[str]) -> Optional[str]:
    # namesAlt 배열에서 "NAME "로 시작하는 첫 항목을 골라 그 뒤 부분을 name_en으로 사용
    for item in names_alt:
        t = str(item).strip()
        if t.upper().startswith("NAME "):
            return t[5:].strip()
    return None

def extract_common_names(names_alt: list[str]) -> list[str]:
    """namesAlt에서 NAME … 형식의 모든 공용 명칭을 추출 (중복/공백 정리)."""
    out = []
    for item in names_alt or []:
        t = str(item).strip()
        if t.upper().startswith("NAME "):
            name = t[5:].strip()
            if name and name not in out:
                out.append(name)
    return out
    
def choose_primary_en(common_names: list[str], fallbacks: list[str]) -> str:
    """
    대표 영어 이름 선택:
    1) KO_MAP에 등록된 이름이면 최우선
    2) 'star', 'nebula', 'cluster' 같은 일반어 포함 안 된 단어 선호
    3) 가장 짧은(단어 수/길이) 이름
    4) 그래도 없으면 fallbacks 첫 유효값
    """
    cand = [n for n in common_names if n]
    # 1) KO_MAP 최우선
    for n in cand:
        if n in KO_MAP:
            return n
    # 2) 일반어(덜 고유한) 패턴 점수화
    def score(n: str) -> tuple:
        low = n.lower()
        generic = any(w in low for w in [" star", " nebula", " cluster", " galaxy", " variable", " a ", " b "])
        words = len(n.split())
        return (generic, words, len(n))  # generic=False(0)가 더 우선, 단어 수/길이 적을수록 우선
    if cand:
        cand.sort(key=score)
        return cand[0]
    # 4) fallbacks
    for f in fallbacks:
        if f:
            return f
    return ""

    
def normalize_bsc5p_known_schema(
    stars: Iterable[Dict[str, Any]],
    mag_threshold: Optional[float],
    commonnames_only: bool
) -> List[Dict[str, Any]]:
    out = []
    for s in stars:
        magnitude = float_or_none(s.get("visualMagnitude"))
        if mag_threshold is not None and magnitude is not None and magnitude > mag_threshold:
            continue

        # 후보 ID들
        bayer = norm_str(s.get("bayerAndOrFlamsteed"))
        hd = norm_str(s.get("hdId"))
        sao = norm_str(s.get("saoId"))
        sid = first(
            bayer,
            (f"HD {hd}" if hd else None),
            (f"SAO {sao}" if sao else None),
            norm_str(s.get("dmId")),
            norm_str(s.get("adsId")),
        ) or f"line:{s.get('lineNumber','?')}"

        # namesAlt 처리
        names_alt = s.get("namesAlt") or []
        common_list = extract_common_names(names_alt)  # ["Dog Star", "Sirius", "Sirius A", ...]
        if commonnames_only and not common_list:
            continue

        # 대표 영어 이름 고르기
        primary_en = choose_primary_en(
            common_list,
            fallbacks=[bayer, sid]  # 공용명이 없다면 Bayer/ID로
        )
        primary_en = norm_str(primary_en) or (bayer or sid)

        # 별칭들: 대표 포함/미포함 모두 일관되게 처리
        # 중복 제거 & 대표가 가장 앞에 오도록
        aliases_en = []
        seen = set()
        for n in ([primary_en] + [x for x in common_list if x != primary_en and x]):
            if n not in seen:
                aliases_en.append(n)
                seen.add(n)

        # 한글: KO_MAP 우선, 없으면 발음 변환. aliases_kr도 병기
        name_kr = KO_MAP.get(primary_en) or eng_to_hangul(primary_en)
        aliases_kr = [KO_MAP.get(n) or eng_to_hangul(n) for n in aliases_en]

        # 좌표
        ra_str = bsc5p_build_hms(s)
        dec_str = bsc5p_build_dms(s)

        spectral = norm_str(s.get("spectralType"))

        out.append({
            "id": sid,
            "catalog": "BrightStar",
            "name_en": primary_en,
            "name_kr": name_kr,
            "aliases_en": aliases_en,   # ✅ 추가: 영어 별칭들
            "aliases_kr": aliases_kr,   # ✅ 추가: 한글 발음 별칭들
            "bayerFlamsteed": bayer,    # ✅ 검색용 보조키
            "ra": ra_str,
            "dec": dec_str,
            "magnitude": magnitude,
            "spectralType": spectral,
            "constellation": None,
        })
    return out

# ---------------- 태양계 기본 목록 ----------------
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
            "type": "Planet" if en not in ("Ganymede", "Titan", "Pluto")
                    else ("Moon" if en in ("Ganymede", "Titan") else "DwarfPlanet"),
            "constellation": None,
        })
    return out

# ---------------- 메인 ----------------
def main():
    ap = argparse.ArgumentParser(description="simpleMessier + bsc5p_extra(namesAlt 지원) → 한/영 병기 통합 카탈로그")
    ap.add_argument("--messier", required=True, help="Messier master_data.json (수정된 포맷)")
    ap.add_argument("--bsc5p", required=True, help="bsc5p_extra.json (namesAlt 포함)")
    ap.add_argument("--out", default="catalog_ko_en.json", help="출력 파일")
    ap.add_argument("--bsc5p-mag", default="6.5", help="BSC5P 임계 등급(이하만 포함). 'none'이면 비활성")
    ap.add_argument("--bsc5p-commonnames-only", action="store_true",
                    help="namesAlt에 'NAME ' 공용명이 있는 별만 포함")
    args = ap.parse_args()

    # 등급 임계값 파싱
    mag_thr = None if str(args.bsc5p_mag).lower() == "none" else float_or_none(args.bsc5p_mag)

    # 입력 로드
    with Path(args.messier).open("r", encoding="utf-8") as f:
        messier_raw = json.load(f)
    with Path(args.bsc5p).open("r", encoding="utf-8") as f:
        bsc5p_raw = json.load(f)

    messier_iter = messier_raw if isinstance(messier_raw, list) else messier_raw.get("data", [])
    bsc5p_iter = bsc5p_raw if isinstance(bsc5p_raw, list) else bsc5p_raw.get("data", [])

    messier = normalize_messier_simple(messier_iter)
    bright  = normalize_bsc5p_known_schema(bsc5p_iter, mag_thr, args.bsc5p_commonnames_only)
    solar   = build_solar_bodies()

    # 병합(id 기준)
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
        by_id[i] = fill_missing(by_id[i], item) if i in by_id else item

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