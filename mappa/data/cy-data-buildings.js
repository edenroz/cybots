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

/* =========================================================================
   DESCRIZIONI PER EDIFICI "DI DEFAULT" (i palazzi 3D generati dallo stile
   OpenStreetMap, NON i cubi disegnati a mano di CUSTOM_BUILDING_DESCRIPTIONS
   qui sotto). Un edificio di default non ha di suo nessun ID stabile: quello
   della vector tile (feature.id) NON è garantito restare lo stesso da un
   caricamento all'altro delle tile, quindi non si può usare come chiave
   persistente in un file di dati. Usiamo invece il centroide della sua
   geometria (arrotondato a 6 decimali, ~11cm di precisione), che è sempre
   lo stesso finché l'edificio stesso non cambia forma — la stessa identica
   chiave già usata internamente da buildingCacheKey()/getBuildingId() in
   index.html per la cache degli indirizzi.

   COME TROVARE L'ID DI UN EDIFICIO: clicca sul palazzo sulla mappa. Il
   pannello mostra sempre, in fondo (nota ciano), il suo ID e la via più
   vicina — anche se l'edificio è ancora "anonimo". Copia quell'ID qui
   sotto per assegnargli nome/blurb.

   Formato voce:
     {
       id: "18.048432,59.331200",  // ID edificio, vedi sopra
       name: "Nome mostrato nel pannello",
       color: "#e8c93a",           // opzionale, default giallo
       blurb: "Testo/HTML del pannello"
     }
   A differenza di CUSTOM_BUILDING_DESCRIPTIONS, qui NON viene disegnato
   nessun cubo aggiuntivo: la descrizione si applica direttamente
   all'edificio 3D già esistente.
   ========================================================================= */
const DEFAULT_BUILDING_DESCRIPTIONS = [
  // Esempio (rimuovi pure, o modificalo):
  {
    id: "17.890113,59.344998",
    name: "Deposito di @qualcuno",
    color: "#e8c93a",
    blurb: "Descrizione dell'edificio."
  },
  {
    id: "17.882255,59.348307",
    name: "Casa di @viff_12344",
    color: "#4ee83a",
    blurb: "Unitá abitativa di @viff_12344, con accesso sul vicolo posteriore.",
    street: "REBOOT PASSAGE",
    number: 135,
    subAddress: "a7_832<br><small>Svarta</small>",
  },
  {
    id: "17.988209,59.297426",
    name: "Casa del CTO",
    color: "#e83adf",
    street: "NEON HIDEOUT",
    number: 239,
    blurb: "Casa.<img src=\"img/casa-cto.jpg\" alt=\"Mia Immagine\">",
    subAddress: "277_3<br><small>South Central</small>",
  },
  {
    id: "17.882019,59.345687",
    name: "Shop 2",
    color: "#3ab7e8",
    street: "FUTURA MALUM™ PATH",
    number: 220,
    blurb: "Dr",
    subAddress: "8_94<br><small>Svarta</small>",
  },
  {
    id: "17.882019,59.345687",
    name: "Shop 1",
    color: "#3ab7e8",
    street: "FUTURA MALUM™ PATH",
    number: 220,
    blurb: "ILG",
    subAddress: "12_24<br><small>Svarta</small>",
  },
  {
    id: "18.041158,59.250170",
    name: "Crash Kids Hideout",
    color: "#ec2828",
    street: "TOXIC YARD",
    number: 61,
    blurb: "<img src=\"img/crash-kids.png\" alt=\"Mia Immagine\">Discarica industriale dove vivono i Crash Kids",
    subAddress: "<br><small>Burnchurch Hex</small>",
  },
  {
    id: "18.026666,59.259151",
    name: "Shop",
    color: "#3ab7e8",
    street: "CORE CHUTE",
    number: 64,
    blurb: "Dr e ILG",
    subAddress: "<br><small>Burnchurch Hex</small>",
  },
  {
    id: "18.027384,59.257122",
    name: "Chiesa",
    color: "#cd00d4",
    blurb: "Chiesa.<img src=\"img/hex-church.jpg\" alt=\"Mia Immagine\">"
  },
  {
    id: "18.027725,59.256882",
    name: "Chiesa",
    color: "#cd00d4",
    blurb: "Chiesa.<img src=\"img/hex-church.jpg\" alt=\"Mia Immagine\">"
  }
];

const CUSTOM_BUILDING_DESCRIPTIONS = [
  {
    street: "PHANTOM YARD",
    number: 327,
    subAddress: "a0_24<br><small>Svarta</small>",
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
    subAddress: "16_654<br><small>Svarta</small>",
    lng: 17.88497,
    lat: 59.34311,
    radius: 0.00006,
    name: "//Conglomerato #417 edificio AB<br>//Livelllo 16 Unitá IN §0_24",
    rotation: 30, // opzionale, in gradi (0 = nord)
    color: "#d41900",
    blurb: "Negozio Droghe",
    height: 18,   // opzionale — se omesso: 1.5
    base: 16
  },
  {
    street: "OVERCLOCK YARD",
    number: 10,
    subAddress: "a5_654<br><small>Burnchurch Hex</small>",
    lng: 18.02786,
    lat: 59.25712,
    radius: 0.00006,
    name: "NEW LIFE HEX CHURCH",
    rotation: 30, // opzionale, in gradi (0 = nord)
    color: "#cd00d4",
    blurb: "Chiesa.<img src=\"img/hex-church.jpg\" alt=\"Mia Immagine\">",
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
    base: 69,
    color: "#cd00d4",
    blurb: "Chiesa.<img src=\"img/hex-church.jpg\" alt=\"Mia Immagine\">",
    blurb: "..."
  }
];
