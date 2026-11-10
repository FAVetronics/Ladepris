# ladepris

Viser den billigste oplademulighed lige nu, målt som gennemsnitlig kr/kWh over den kommende time:

- **Hjemme:** Vindstød Elforbundet.dk 2026 + Ikast El Net (alt inkl.), via [Strømligning](https://stromligning.dk)
- **Nærmeste Tesla, Circle K og OK** ud fra GPS. `chargers.json` bygges hver time af GitHub Actions (`tools/build_chargers.py`): Tesla fra supercharge.info, Circle K/OK fra OpenStreetMap, priser fra circlek.dk og ok.dk. Tesla-prisen indtastes manuelt (ingen åben pris-API).

Åbn: https://favetronics.github.io/Ladepris/

## batteri/

Tilbagebetalingstid for et nettilsluttet batteri som funktion af årligt forbrug, regnet på historiske timepriser fra Strømligning (samme elprodukt, transport og afgifter som ladepris). To kurver: kun eget forbrug, og med salg til nettet (spotpris minus dit gebyr).

Åbn: https://favetronics.github.io/Ladepris/batteri/
