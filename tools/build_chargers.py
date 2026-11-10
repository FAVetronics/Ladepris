"""Bygger chargers.json til appen. Køres af GitHub Actions (.github/workflows/chargers.yml).

Kilder (alle verificeret 2026-11-10):
  Tesla-lokationer : supercharge.info  /service/supercharge/allSites
  OK/Circle K-lok. : OpenStreetMap via Overpass (amenity=charging_station, operator/brand)
  Circle K-pris    : circlek.dk/priser  – rækken "El-Lynlader" (listepris inkl. moms + dato)
  OK-priser        : ok.dk ladestander-priser – vejledende pr. ladertype (inkl. moms + dato)
Fejler en kilde eller ser data forkert ud, stopper scriptet, og den gamle fil bevares.
"""
import json, re, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

UA = {"User-Agent": "favetronics-ladepris (github.com/FAVetronics/Ladepris)"}
def get(url, data=None):
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA), timeout=120) as r:
        return r.read()
def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
def num(s):
    return float(s.replace(".", "").replace(",", "."))
def die(msg):
    sys.exit("FEJL: " + msg)

# ---------- Tesla ----------
TESLA_URL = "https://supercharge.info/service/supercharge/allSites"
tesla = []
for s in json.loads(get(TESLA_URL)):
    a, g = s.get("address") or {}, s.get("gps") or {}
    if a.get("country") == "Denmark" and s.get("status") in ("OPEN", "EXPANDING") and g.get("latitude") is not None:
        tesla.append({"op": "tesla", "name": s.get("name"), "lat": g["latitude"], "lon": g["longitude"],
                      "stalls": s.get("stallCount"), "kw": s.get("powerKilowatt"), "dc": True})
print(f"Tesla: {len(tesla)}")
if len(tesla) < 20: die("for få Tesla-lokationer")

# ---------- OK / Circle K fra OpenStreetMap ----------
Q = """[out:json][timeout:150];area["ISO3166-1"="DK"][admin_level=2]->.dk;
nwr["amenity"="charging_station"](area.dk)->.cs;
(nwr.cs["operator"~"circle ?k",i]; nwr.cs["brand"~"circle ?k",i];
 nwr.cs["operator"~"^ok$",i]; nwr.cs["brand"~"^ok$",i];);
out center tags;"""
try:
    previous = json.load(open("chargers.json", encoding="utf-8"))
except FileNotFoundError:
    previous = None

# Overpass er ustabil (502/timeout set 2026-11-10): flere forsøg, ellers genbrug forrige lokationer.
import time
osm = None
for attempt in range(3):
    for ep in ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]:
        try:
            osm = json.loads(get(ep, urllib.parse.urlencode({"data": Q}).encode())); break
        except Exception as e:
            print(f"Overpass fejl (forsøg {attempt+1})", ep, repr(e))
    if osm: break
    time.sleep(60)

def kw_of(t):
    """Højeste effekt angivet i *:output-tags (kW), eller None."""
    best = None
    for k, v in t.items():
        if k.endswith(":output"):
            for m in re.finditer(r"([\d.]+)\s*(kW|W)?", v, re.I):
                val = float(m.group(1)) / (1000 if (m.group(2) or "").lower() == "w" else 1)
                best = val if best is None else max(best, val)
    return best

others = []
for e in (osm or {"elements": []})["elements"]:
    t = e.get("tags", {})
    lab = " ".join(t.get(k, "") for k in ("operator", "brand")).lower()
    op = "circlek" if re.search(r"circle ?k", lab) else "ok" if re.search(r"(^|\s)ok($|\s)", lab) else None
    if not op: continue
    if t.get("access") in ("private", "customers", "no"): continue
    c = e.get("center", e)
    dc = True if any(k in t for k in ("socket:type2_combo", "socket:chademo")) else None
    others.append({"op": op, "name": t.get("name") or ("Circle K" if op == "circlek" else "OK"),
                   "lat": c["lat"], "lon": c["lon"], "kw": kw_of(t), "dc": dc,
                   "stalls": int(t["capacity"]) if t.get("capacity", "").isdigit() else None,
                   "osm": f"{e['type']}/{e['id']}"})
if osm is None:
    if not previous: die("ingen Overpass-server svarede, og der er ingen tidligere lokationer")
    others = [x for x in previous["sites"] if x["op"] in ("circlek", "ok")]
    print("Overpass utilgængelig – genbruger forrige OK/Circle K-lokationer")
n_ck = sum(o["op"] == "circlek" for o in others); n_ok = len(others) - n_ck
print(f"OSM: Circle K {n_ck}, OK {n_ok}")
if n_ck < 50 or n_ok < 200: die("for få OSM-lokationer")

# ---------- Priser ----------
ck = text(get("https://www.circlek.dk/priser").decode("utf-8", "replace"))
m = re.search(r"El-Lynlader\s+Pris inkl\. moms:\s*([\d,]+)\s+Dato:\s*(\d{4}-\d{2}-\d{2})", ck)
if not m: die("Circle K-pris ikke fundet på circlek.dk/priser")
ck_price = {"lyn": num(m.group(1)), "date": m.group(2), "source": "https://www.circlek.dk/priser",
            "note": "Listepris for lynladning"}
print("Circle K:", ck_price)

okt = text(get("https://www.ok.dk/privat/produkter/opladning/ude/ladestander-priser").decode("utf-8", "replace"))
okp = {}
for cls, key in (("Normallader", "normal"), ("Hurtiglader", "hurtig"), ("Lynlader", "lyn")):
    m = re.search(cls + r" \([^)]*\) ([\d,]+) kr\./kWh", okt)
    if not m: die(f"OK-pris for {cls} ikke fundet")
    okp[key] = num(m.group(1))
m = re.search(r"gældende d\. (\d{2})\.(\d{2})\.(\d{4})", okt)
if not m: die("OK-prisdato ikke fundet")
ok_price = {**okp, "date": f"{m.group(3)}-{m.group(2)}-{m.group(1)}",
            "source": "https://www.ok.dk/privat/produkter/opladning/ude/ladestander-priser",
            "note": "Vejledende pris; kan afvige for enkelte lokationer"}
print("OK:", ok_price)
for v in [ck_price["lyn"], *okp.values()]:
    if not 1 < v < 10: die(f"urimelig pris {v}")

out = {"prices": {"circlek": ck_price, "ok": ok_price},
       "sources": {"tesla": TESLA_URL, "osm": "© OpenStreetMap-bidragydere (ODbL)"},
       "sites": sorted(tesla + others, key=lambda s: (s["op"], s["name"] or "", s["lat"]))}
old = dict(previous) if previous else None
if old: old.pop("built", None)
if out != old:
    out["built"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open("chargers.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
    print("chargers.json opdateret")
else:
    print("ingen ændring")
