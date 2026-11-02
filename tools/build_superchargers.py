"""Henter alle Tesla Supercharger-lokationer fra supercharge.info og skriver de
åbne danske til superchargers.json. Køres af GitHub Actions (se workflows)."""
import json, sys, urllib.request

URL = "https://supercharge.info/service/supercharge/allSites"
OK_STATUS = {"OPEN", "EXPANDING"}

req = urllib.request.Request(URL, headers={"User-Agent": "favetronics-ladepris (github.com/FAVetronics/Ladepris)"})
with urllib.request.urlopen(req, timeout=60) as r:
    sites = json.load(r)

print(f"hentet {len(sites)} sites i alt")
out = []
for s in sites:
    addr = s.get("address") or {}
    if addr.get("country") != "Denmark":
        continue
    if s.get("status") not in OK_STATUS:
        continue
    gps = s.get("gps") or {}
    lat, lon = gps.get("latitude"), gps.get("longitude")
    if lat is None or lon is None:
        continue
    out.append({"name": s.get("name"), "lat": lat, "lon": lon,
                "stalls": s.get("stallCount"), "status": s.get("status"),
                "city": addr.get("city")})

out.sort(key=lambda x: x["name"] or "")
print(f"{len(out)} åbne danske Superchargere")
for o in out:
    print(f"  {o['name']:<40} {o['lat']:.5f},{o['lon']:.5f}  {o['stalls']} stalls  {o['status']}")

# Sanity: Danmark har ~40 lokationer. Langt færre betyder at formatet er ændret.
if len(out) < 20:
    sys.exit(f"FEJL: kun {len(out)} danske sites – formatet hos supercharge.info er måske ændret")

with open("superchargers.json", "w", encoding="utf-8") as f:
    json.dump({"source": URL, "sites": out}, f, ensure_ascii=False, indent=1)
