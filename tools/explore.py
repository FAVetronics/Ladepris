"""Engangs-undersøgelse: hvad returnerer de mulige datakilder? Skriver kun til loggen."""
import json, re, urllib.request, urllib.parse, io
UA={"User-Agent":"favetronics-ladepris (github.com/FAVetronics/Ladepris)"}
def get(url, data=None, n=None):
    req=urllib.request.Request(url, data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        b=r.read(); print(f"\n##### {url}\nHTTP {r.status} {r.headers.get('content-type')} {len(b)} bytes"); return b

def safe(f):
    try: f()
    except Exception as e: print("FEJL:", repr(e))

def osm():
    q='''[out:json][timeout:120];area["ISO3166-1"="DK"][admin_level=2]->.dk;
    nwr["amenity"="charging_station"](area.dk)->.cs;
    (nwr.cs["operator"~"circle ?k",i]; nwr.cs["brand"~"circle ?k",i]; nwr.cs["network"~"circle ?k",i];
     nwr.cs["operator"~"^ok( |$|\\\\b)",i]; nwr.cs["brand"~"^ok( |$|\\\\b)",i]; nwr.cs["network"~"^ok( |$|\\\\b)",i];);
    out center tags;'''
    for ep in ["https://overpass-api.de/api/interpreter","https://overpass.private.coffee/api/interpreter"]:
        try:
            d=json.loads(get(ep, data=urllib.parse.urlencode({"data":q}).encode()))
            els=d["elements"]; print(len(els),"elementer")
            from collections import Counter
            print("operator:",Counter((e.get("tags",{}).get("operator"),e.get("tags",{}).get("brand")) for e in els).most_common(20))
            keys=Counter(k for e in els for k in e.get("tags",{}))
            print("tag-nøgler:",keys.most_common(40))
            for e in els[:6]: print(json.dumps(e,ensure_ascii=False)[:600])
            return
        except Exception as e: print("FEJL",ep,repr(e))

def ck_export():
    b=get("https://www.circlek.dk/export/price/28"); print(b[:1500])
def ck_pdf():
    b=get("https://www.circlek.dk/media-assets/uploads/2026-03/DK%20Fuel%20Prices%20API%20doc%202_1.pdf")
    from pypdf import PdfReader
    print("\n".join(p.extract_text() for p in PdfReader(io.BytesIO(b)).pages)[:6000])
def ck_page():
    t=get("https://www.circlek.dk/priser").decode("utf-8","replace")
    i=t.find("EV Charger"); print(re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t[i-300:i+900])))
def ok_page():
    t=get("https://www.ok.dk/privat/produkter/opladning/ude/ladestander-priser").decode("utf-8","replace")
    txt=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t))
    for m in re.finditer(r"(Normallader|Hurtiglader|Lynlader)[^.]{0,80}?kr\./kWh",txt): print("  ",m.group(0))
    m=re.search(r"gældende d\. [0-9.]+",txt); print("  ",m and m.group(0))
    for k in ["api","json","chargingStation","ladestander"]:
        for m in re.finditer(r'["\'](https?://[^"\']*%s[^"\']*)["\']'%k,t,re.I): print("  url:",m.group(1))
def ok_api():
    d=json.loads(get("https://mobility-prices.ok.dk/api/v1/fuel-prices"))
    prods=sorted({p["product_name"] for s in d["items"] for p in s["prices"]}); print(len(d["items"]),"stationer; produkter:",prods)

for f in [osm, ck_export, ck_page, ck_pdf, ok_page, ok_api]: safe(f)
