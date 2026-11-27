"""Stage pinned public race facts; accept only corroborated identities/positions/points."""

import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import unicodedata
import zipfile

import requests

from category_scope import canonical_category, normalize_category
from sql_connection import connect_to_sql


SOURCE_ID = "kaggle-amalsalilan-motogp-de114c7c"
SOURCE_URL = "https://www.kaggle.com/datasets/amalsalilan/motogpresultdataset"
DOWNLOAD_URL = "https://www.kaggle.com/api/v1/datasets/download/amalsalilan/motogpresultdataset"
CSV_HASH = "de114c7cdccc9850c645c2fc1569efcfbf31ae534b01ac336e80a87eb3cdb76f"
SCORING_URL = "http://racingmemo.fr/aa-legendesgrilles.htm"
TT_URL = "https://www.iomtt.com/tt-database/events/races?meet_code=TT66&race_seq=6"
# Individually cross-checked factual results, not a bulk copy of the TT database.
CORROBORATION = {
    (1966, "500cc", "TT", "mikehailwood"): (1, "Honda", TT_URL),
    (1966, "500cc", "TT", "giacomoagostini"): (2, "MV Agusta", TT_URL),
}


def name_key(value):
    if "," in value:
        surname, given = value.split(",", 1)
        value = f"{given} {surname}"
    return "".join(
        c for c in unicodedata.normalize("NFKD", value).casefold() if c.isalnum()
    )


def expected_points(year, position):
    if 1950 <= year <= 1968:
        scores = (8, 6, 4, 3, 2, 1)
    elif 1969 <= year <= 1987:
        scores = (15, 12, 10, 8, 6, 5, 4, 3, 2, 1)
    elif 1988 <= year <= 1989:
        scores = (20, 17, 15, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1)
    else:
        # 1949 included a fastest-lap point; finishing position is insufficient.
        return None
    return Decimal(scores[position - 1] if position <= len(scores) else 0)


def load_csv(path):
    if not path.exists():
        response = requests.get(DOWNLOAD_URL, timeout=90)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            content = archive.read("FILTERED_ROWS.csv")
        if hashlib.sha256(content).hexdigest() != CSV_HASH:
            raise ValueError("Public dataset changed; review the new source before accepting it")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != CSV_HASH:
        raise ValueError("Cached dataset fingerprint mismatch")
    return list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))


def catalog(conn):
    identities = defaultdict(set)
    for year, category, rid, name in conn.execute("""
        SELECT cs.season_year,cs.category,cs.rider_id,r.full_name
        FROM championship_standings cs JOIN riders r ON r.rider_id=cs.rider_id
        UNION
        SELECT e.season_year,s.category,c.rider_id,r.full_name
        FROM classifications c JOIN sessions s ON s.session_id=c.session_id
        JOIN events e ON e.event_id=s.event_id JOIN riders r ON r.rider_id=c.rider_id
    """).fetchall():
        identities[(year, normalize_category(category), name_key(name))].add(rid)
    sessions = defaultdict(set)
    official = {}
    for year, category, event, sid, rid, pos, points in conn.execute("""
        SELECT e.season_year,s.category,e.short_name,s.session_id,c.rider_id,c.position,c.points
        FROM sessions s JOIN events e ON e.event_id=s.event_id
        LEFT JOIN classifications c ON c.session_id=s.session_id
        WHERE s.session_type='RAC' AND s.status='FINISHED' AND s.source_kind='official-api'
    """).fetchall():
        sessions[(year, normalize_category(category), event)].add(sid)
        if rid:
            official[(sid, rid)] = (pos, points)
    return identities, sessions, official


def assess(row, identities, sessions, official):
    year = int(row["year"])
    category = canonical_category(row["category"])
    base = (year, normalize_category(category))
    key = (*base, row["shortname"])
    ids = identities.get((*base, name_key(row["rider_name"])), set())
    races = sessions.get(key, set())
    result = {
        "session_id": None, "rider_id": None, "decision": "held",
        "reason": "", "evidence_url": None, "position": None, "points": None,
        "constructor_name": None,
    }
    if len(ids) != 1 or len(races) != 1:
        result["reason"] = "No unique official season/class rider and race mapping"
        return result
    result.update(session_id=next(iter(races)), rider_id=next(iter(ids)))
    try:
        position = int(row["position"])
        points = Decimal(row["points"])
        if position <= 0 or not points.is_finite() or points < 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        result["reason"] = "Undocumented status/position or invalid points"
        return result
    result["position"] = position
    existing = official.get((result["session_id"], result["rider_id"]))
    if existing:
        if existing[0] != position:
            result["reason"] = "Position conflicts with official result"
            return result
        result.update(decision="corroborated", reason="Position agrees with official result; timings not imported",
                      evidence_url="https://api.motogp.pulselive.com/motogp/v1/results/session/"
                      + result["session_id"] + "/classification")
        if existing[1] is not None:
            if Decimal(str(existing[1])) != points:
                result.update(decision="held", reason="Points conflict with official result")
            return result
    else:
        evidence = CORROBORATION.get((year, category, row["shortname"], name_key(row["rider_name"])))
        if not evidence or evidence[0] != position or evidence[1] != row["bike_name"]:
            result["reason"] = "Missing official result requires independent field-level corroboration"
            return result
        result.update(evidence_url=evidence[2], constructor_name=evidence[1])
    score = expected_points(year, position)
    if score is None or points != score:
        result["reason"] = "Points require additional evidence (bonus, shortened race, or disagreement)"
        return result
    result.update(
        decision="accepted", points=float(points),
        reason=f"Position/identity corroborated; points agree with {SCORING_URL}; timings not imported",
    )
    return result


def candidate_id(row):
    payload = json.dumps(row, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256((SOURCE_ID + payload).encode()).hexdigest()


def verify(conn, rows, decisions):
    expected = {candidate_id(row): d for row, d in zip(rows, decisions)}
    actual = conn.execute("""
        SELECT candidate_id,decision,session_id,rider_id FROM external_candidates WHERE source_id=?
    """, SOURCE_ID).fetchall()
    checked = {
        cid: (decision, sid, rid) for cid, decision, sid, rid in actual if cid in expected
    }
    if checked != {cid: (d["decision"], d["session_id"], d["rider_id"]) for cid, d in expected.items()}:
        raise ValueError("Stored external decisions differ from the audit")
    actual = conn.execute("""
        SELECT x.candidate_id,x.position,x.points,x.constructor_name
        FROM external_classifications x JOIN external_candidates c ON c.candidate_id=x.candidate_id
        WHERE c.source_id=?
    """, SOURCE_ID).fetchall()
    checked = {cid: (pos, pts, constructor) for cid, pos, pts, constructor in actual if cid in expected}
    if checked != {
        cid: (d["position"], d["points"], d["constructor_name"])
        for cid, d in expected.items() if d["decision"] == "accepted"
    }:
        raise ValueError("Accepted external facts differ from the verified audit")


def persist(conn, rows, decisions, rollback=False):
    with conn:
        cursor = conn.cursor()
        current = cursor.execute(
            "SELECT content_hash FROM external_sources WHERE source_id=?", SOURCE_ID,
        ).fetchone()
        if current and current[0] != CSV_HASH:
            raise ValueError("Registered external source fingerprint differs")
        cursor.execute("""
            IF NOT EXISTS (SELECT 1 FROM external_sources WHERE source_id=?)
            INSERT INTO external_sources(source_id,source_url,declared_license,content_hash)
            VALUES (?,?,?,?)
        """, SOURCE_ID, SOURCE_ID, SOURCE_URL, "Publisher-declared CC0", CSV_HASH)
        candidate_params, accepted_params, held_params = [], [], []
        for row, decision in zip(rows, decisions):
            payload = json.dumps(row, sort_keys=True, ensure_ascii=True)
            cid = candidate_id(row)
            candidate_params.append((
                cid, decision["decision"], decision["reason"], decision["session_id"],
                decision["rider_id"], decision["evidence_url"],
                cid, SOURCE_ID, int(row["year"]), canonical_category(row["category"]),
                row["shortname"], row["rider_name"], payload, decision["decision"],
                decision["reason"], decision["session_id"], decision["rider_id"], decision["evidence_url"],
            ))
            if decision["decision"] == "accepted":
                accepted_params.append((
                    decision["session_id"], decision["rider_id"], cid, decision["position"],
                    decision["constructor_name"], decision["points"],
                    decision["session_id"], decision["rider_id"], cid, decision["position"],
                    decision["constructor_name"], decision["points"],
                ))
            else:
                held_params.append((cid,))
        cursor.fast_executemany = True
        for offset in range(0, len(candidate_params), 500):
            cursor.executemany("""
                MERGE external_candidates AS t USING (SELECT ? AS candidate_id) AS s
                ON t.candidate_id=s.candidate_id
                WHEN MATCHED THEN UPDATE SET decision=?,reason=?,session_id=?,rider_id=?,
                    evidence_url=?,decided_at=SYSUTCDATETIME()
                WHEN NOT MATCHED THEN INSERT
                    (candidate_id,source_id,season_year,category,event_short,rider_name,source_json,
                     decision,reason,session_id,rider_id,evidence_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?);
            """, candidate_params[offset:offset + 500])
        if held_params:
            cursor.executemany(
                "DELETE FROM external_classifications WHERE candidate_id=?", held_params,
            )
        for offset in range(0, len(accepted_params), 500):
            cursor.executemany("""
                MERGE external_classifications AS t
                USING (SELECT ? AS session_id,? AS rider_id) AS s
                ON t.session_id=s.session_id AND t.rider_id=s.rider_id
                WHEN MATCHED THEN UPDATE SET candidate_id=?,position=?,constructor_name=?,points=?
                WHEN NOT MATCHED THEN INSERT
                    (session_id,rider_id,candidate_id,position,constructor_name,points)
                VALUES (?,?,?,?,?,?);
            """, accepted_params[offset:offset + 500])
        verify(conn, rows, decisions)
        if rollback:
            conn.rollback()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--categories", default="500cc")
    parser.add_argument("--csv", type=Path, default=Path("historical_cache") / "external" / "FILTERED_ROWS.csv")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true", help="Verify a write transaction, then roll it back")
    args = parser.parse_args()
    categories = {canonical_category(c) for c in args.categories.split(",")}
    rows = [
        row for row in load_csv(args.csv)
        if 1949 <= int(row["year"]) <= 1989 and row["category"] in categories
    ]
    with connect_to_sql() as conn:
        catalog_data = catalog(conn)
        decisions = [assess(row, *catalog_data) for row in rows]
        accepted_keys = Counter(
            (d["session_id"], d["rider_id"]) for d in decisions if d["decision"] == "accepted"
        )
        for decision in decisions:
            if decision["decision"] == "accepted" and accepted_keys[(decision["session_id"], decision["rider_id"])] > 1:
                decision.update(decision="held", points=None, reason="Multiple source rows map to the same rider/race")
        print(json.dumps({
            "candidates": len(rows), "decisions": dict(Counter(d["decision"] for d in decisions)),
            "held_reasons": dict(Counter(d["reason"] for d in decisions if d["decision"] == "held")),
        }, indent=2), flush=True)
        if args.apply:
            persist(conn, rows, decisions, rollback=args.rollback)
            print("External transaction verified and rolled back." if args.rollback else
                  "Audited external facts persisted separately; official snapshots and standings unchanged.")


if __name__ == "__main__":
    main()
