/* =========================================================================
   CY — DATI: VIE PRECARICATE + DESCRIZIONI EDIFICI PERSONALIZZATI
   Incolla qui, byte-per-byte, il blocco originale:
     const PRELOADED_STREETS = [ ... ];
     const CUSTOM_BUILDING_DESCRIPTIONS = [ ... ];
   ========================================================================= */

const PRELOADED_STREETS = [
  {
    name: "VECTOR STREET",
    lng: 18.06838,
    lat: 59.26100
  },
  {
    name: "DRIFT TRENCH, #1",
    lng: 17.87422,
    lat: 59.35089
  },
  {
    name: "TOXIC YARD",
    lng: 18.04120,
    lat: 59.250015
  }
];

const CUSTOM_BUILDING_DESCRIPTIONS = [
  {
    // Esempio già pronto: l'edificio #31 di REBOOT PASSAGE che hai
    // citato. Ho anche aggiunto l'aggancio per coordinate, usando lo
    // stesso punto già presente in PRELOADED_STREETS qui sopra, così hai
    // subito un fallback stabile — modifica pure name/blurb come vuoi,
    // oppure elimina la riga lng/lat/radius se preferisci affidarti solo
    // al civico.
    street: "REBOOT PASSAGE",
    number: 31,
    subAddress: "a7_832",
    lng: 17.882245,
    lat: 59.34839,
    radius: 0.0006,
    name: "//Conglomerato #31 edificio A<br>//Livelllo 3 Unitá AB §3_832",
    rotation: 50, // opzionale, in gradi (0 = nord)
    color: "#1FD400",
    blurb: "Unitá abitativa di Lear, con accesso sul vicolo posteriore.",
    height: 4.5,   // opzionale — se omesso: 1.5
    base: 3
  },
  {
    street: "PHANTOM YARD",
    number: 327,
    subAddress: "a0_24",
    lng: 17.87761,
    lat: 59.34801,
    radius: 0.00006,
    name: "//Conglomerato #327 edificio A<br>//Livelllo 0 Unitá IN §0_24",
    rotation: 38, // opzionale, in gradi (0 = nord)
    color: "#07d400",
    blurb: "Laboratorio di distillazione clandestina di @fl4s#_11037.<img src=\"img/moonshine.jpg\" alt=\"Mia Immagine\">"
  },
  {
    street: "NULL CHUTE",
    number: 417,
    subAddress: "d16_654",
    lng: 17.88497,
    lat: 59.34311,
    radius: 0.00006,
    name: "//Conglomerato #417 edificio AB<br>//Livelllo 0 Unitá IN §0_24",
    rotation: 30, // opzionale, in gradi (0 = nord)
    color: "#d41900",
    blurb: "Negozio",
    height: 18,   // opzionale — se omesso: 1.5
    base: 16
  },
  {
    street: "OVERCLOCK YARD",
    number: 10,
    subAddress: "a5_654",
    lng: 18.02790,
    lat: 59.25721,
    radius: 0.00006,
    name: "NEW LIFE HEX CHURCH",
    rotation: 30, // opzionale, in gradi (0 = nord)
    color: "#cd00d4",
    blurb: "Negozio.<img src=\"img/hex-church.jpg\" alt=\"Mia Immagine\">",
    height: 80,   // opzionale — se omesso: 1.5
    base: 0
  },
  {
    street: "OVERCLOCK YARD",
    number: 11,
    polygon: [
[
              18.0279235,
              59.2569935
            ],
            [
              18.0279827,
              59.2570048
            ],
            [
              18.0277737,
              59.2572587
            ],
            [
              18.0277182,
              59.257245
            ],
            [
              18.0279235,
              59.2569935
            ]
      // non serve richiudere l'anello, ci pensa il codice
    ],
    height: 71,
    base: 67,
    color: "#cd00d4",
    name: "//Conglomerato #31...",
    blurb: "..."
  }
];
