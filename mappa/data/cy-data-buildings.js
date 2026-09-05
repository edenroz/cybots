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
    subAddress: "a3_832",
    lng: 17.882245,
    lat: 59.34839,
    radius: 0.0006,
    name: "//Conglomerato #31 edificio A<br>//Livelllo 3 Unitá AB §3_832",
    rotation: 50, // opzionale, in gradi (0 = nord)
    color: "#1FD400",
    blurb: "Unitá abitativa di Lear, con accesso sul vicolo posteriore."
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
  }
];
