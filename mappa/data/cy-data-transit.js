/* =========================================================================
   CY — DATI: RETE DI TRASPORTO (MONOROTAIE MAGNETICHE + BUS)
   Ispirata alla rete reale della metropolitana di Stoccolma (linea rossa/
   verde/blu, con l'hub centrale a T-Centralen), reimmaginata come una rete
   di monorotaie magnetiche sopraelevate che corrono su quasi tutta la CY,
   con linee bus a coprire i distretti più periferici/slum non serviti
   dalle maglev.

   TRANSIT_STATIONS: elenco di tutte le stazioni/fermate, indipendente
   dalle linee. Ogni stazione ha un id univoco, referenziato dagli array
   "stations" di TRANSIT_LINES qui sotto — così un interscambio (stessa
   stazione toccata da più linee) è definito una volta sola e riusato.

   TRANSIT_LINES: ogni linea ha:
     id, name, color, type ("monorail" | "bus"), stations: [id, id, ...]
   L'ordine di "stations" è l'ordine reale di percorrenza della linea.
   ========================================================================= */

const TRANSIT_STATIONS = [
  // --- Interscambi principali (decentrati, nessun hub unico) ---------------
  {
    id: "stz-svarta",
    name: "SVÄRTA CROSSING",
    lng: 17.8840, lat: 59.3440,
    district: "SVÄRTA",
    blurb: "Interscambio tra la linea Sangue e la linea Neon, proprio sopra il quartiere dove un tempo ruggivano le cyberbike. Le banchine portano ancora i segni dei vecchi scontri tra clan: fori di proiettile riempiti di resina, mai davvero nascosti."
  },
  {
    id: "stz-north-central",
    name: "NORTH CENTRAL SPIRE",
    lng: 17.9600, lat: 59.3260,
    district: "NORTH CENTRAL",
    blurb: "Stazione di vetro e acciaio lucido, con un solo accesso per i coffin apartment sottostanti e uno riservato ai piani alti delle arcologie. Due file diverse, due mondi diversi, la stessa banchina."
  },

  // --- LINEA MAGLEV ROSSA "SANGUE" ------------------------------------------
  {
    id: "stz-borghold",
    name: "BORGHOLD TERMINUS",
    lng: 17.8830, lat: 59.3190,
    district: "BORGHOLD",
    blurb: "Capolinea sud della linea Sangue, incastrato tra i blocchi residenziali e il muro del grande complesso carcerario. I turni cambiano qui: chi scende alle 6 del mattino ha lo stesso sguardo di chi risale alle 6 di sera."
  },
  {
    id: "stz-south-central",
    name: "SOUTH CENTRAL EXCHANGE",
    lng: 17.9680, lat: 59.2990,
    district: "SOUTH CENTRAL",
    blurb: "La stazione più sorvegliata della rete: telecamere ogni tre metri, droni di pattuglia sul tetto della banchina, pubblicità della Fideistic Transformation che promette la salvezza a ogni fermata."
  },
  {
    id: "stz-the-arcs",
    name: "ARCS GATE",
    lng: 17.9230, lat: 59.3060,
    district: "THE ARCS",
    blurb: "Il binario si infila letteralmente dentro una delle tre arcologie: la stazione è un piano dell'edificio come un altro, tra un centro commerciale e un reparto ospedaliero."
  },
  {
    id: "stz-happy-town",
    name: "HAPPY TOWN TERMINAL",
    lng: 17.8920, lat: 59.2970,
    district: "HAPPY TOWN II",
    blurb: "Capolinea decorato con murales pastello ormai scrostati, promessa di un futuro migliore che nessuno ha più il tempo di guardare. L'abbonamento mensile costa più della metà dell'affitto."
  },
  {
    id: "stz-crown-island",
    name: "CROWN ISLAND PIER",
    lng: 17.9010, lat: 59.2800,
    district: "CROWN ISLAND",
    blurb: "Capolinea sud della linea Sangue, affacciato sull'acqua. Le vetture che arrivano qui sono sempre le più pulite della flotta: qualcuno paga perché resti così."
  },

  // --- LINEA MAGLEV VERDE "OSSIDO" ------------------------------------------
  {
    id: "stz-ports",
    name: "PORTS GATEWAY",
    lng: 18.0950, lat: 59.3520,
    district: "PORTS",
    blurb: "Capolinea nord della linea Ossido, sospesa sopra moli e container. Il rumore delle gru copre quasi sempre gli annunci vocali delle partenze."
  },
  {
    id: "stz-paradise-spire",
    name: "PARADISE SPIRE JUNCTION",
    lng: 18.0700, lat: 59.3140,
    district: "PARADISE SPIRE",
    blurb: "Banchina stretta tra due file di blocchi residenziali così vicini che, da certi vagoni, si vede dentro le finestre altrui. Nessuno chiude più le tende: tanto vale."
  },
  {
    id: "stz-burnchurch",
    name: "BURNCHURCH HEX DEPOT",
    lng: 18.0300, lat: 59.2710,
    district: "BURNCHURCH HEX",
    blurb: "Deposito e capolinea intermedio, circondato da bancarelle che vendono carne micobiotica a chi scende dal turno di notte. L'odore si sente ben prima di vedere l'insegna."
  },
  {
    id: "stz-lower-walds",
    name: "LOWER WALDS END",
    lng: 17.9350, lat: 59.2500,
    district: "LOWER WALDS",
    blurb: "L'ultima fermata prima che la CY smetta di fingersi città. Da qui in poi, solo rottamai e chi cerca di sparire."
  },
  {
    id: "stz-optima-depths",
    name: "OPTIMA DEPTHS FRINGE",
    lng: 17.8420, lat: 59.2070,
    district: "OPTIMA DEPTHS",
    blurb: "Capolinea sud della linea Ossido e interscambio con la linea bus Outland Express. Le vetture qui arrivano quasi vuote: pochi ammettono di scendere fin qui."
  },

  // --- LINEA MAGLEV BLU "NEON" -----------------------------------------------
  {
    id: "stz-lilypond",
    name: "LILYPOND OUTPOST",
    lng: 17.9880, lat: 59.3670,
    district: "LILYPOND",
    blurb: "Capolinea nord della linea Neon, presidiato da pattuglie armate 24 ore su 24. Salire o scendere qui senza essere notati è quasi impossibile — ed è esattamente il punto."
  },
  {
    id: "stz-bigmosse",
    name: "BIGMOSSE JUNCTION",
    lng: 17.9030, lat: 59.3680,
    district: "BIGMOSSE",
    blurb: "Stazione contesa: metà banchina è tacitamente territorio Virid Vipers, l'altra metà degli Heirs of Kergoz. Una linea di vernice sul pavimento segna il confine. Nessuno la calpesta per sbaglio due volte."
  },
  {
    id: "stz-mosscroft",
    name: "MOSSCROFT WORKS",
    lng: 18.1550, lat: 59.3580,
    district: "MOSSCROFT",
    blurb: "Stazione industriale, i filtri dell'aria lavorano a pieno regime senza mai davvero ripulirla. I turnisti la riconoscono a occhi chiusi dall'odore, molto prima di leggere il nome."
  },
  {
    id: "stz-vertex-nova",
    name: "VERTEX NOVA PLAZA",
    lng: 18.2280, lat: 59.3690,
    district: "VERTEX NOVA",
    blurb: "Banchina lucida, annunci in tre lingue, ogni superficie sponsorizzata. Mosscroft con un ufficio stampa, anche qui."
  },
  {
    id: "stz-evergreen-bay",
    name: "EVERGREEN BAY TERMINUS",
    lng: 18.2150, lat: 59.4000,
    district: "EVERGREEN BAY",
    blurb: "Capolinea est della linea Neon, con vista sulla baia che nessuno dovrebbe più toccare. I cartelloni pubblicitari promettono aria pulita proprio sopra l'acqua che non lo è."
  },

  // --- BUS 07 "CROSSTOWN" -----------------------------------------------------
  {
    id: "stz-laketon",
    name: "LAKETON STOP",
    lng: 18.1050, lat: 59.3030,
    district: "LAKETON",
    blurb: "Pensilina mezza allagata, come tutto il resto del quartiere. Il bus arriva quando arriva: gli orari sono più una speranza che un orario."
  },
  {
    id: "stz-galgbacken",
    name: "GALGBACKEN GATE",
    lng: 18.1010, lat: 59.2920,
    district: "GALGBACKEN",
    blurb: "Fermata privata, sorvegliata quanto le ville circostanti. Il bus che si ferma qui è climatizzato e quasi sempre vuoto."
  },
  {
    id: "stz-quay47",
    name: "QUAY #47 DOCKS",
    lng: 18.2850, lat: 59.2970,
    district: "QUAY #47",
    blurb: "Capolinea tra container impilati e gru automatiche. Le merci che passano da qui non sempre finiscono sul manifesto di carico."
  },
  {
    id: "stz-prophet-park",
    name: "PROPHET PARK SQUARE",
    lng: 18.1800, lat: 59.3070,
    district: "PROPHET PARK",
    blurb: "Fermata circondata da predicatori e venditori di salvezza. Salire sul bus costa meno di qualsiasi redenzione offerta lì fuori."
  },
  {
    id: "stz-cot-square",
    name: "COT SQUARE MARKET",
    lng: 18.1770, lat: 59.2470,
    district: "COT SQUARE",
    blurb: "Capolinea sud della Crosstown, in mezzo al mercato abusivo. Di giorno si vende merce di seconda mano, di notte quella che una prima mano non ha mai avuto."
  },
  {
    id: "stz-low-meadow",
    name: "LOW MEADOW YARD",
    lng: 18.1680, lat: 59.2880,
    district: "LOW MEADOW",
    blurb: "Fermata tra i magazzini, coperta dal rumore costante degli impianti industriali. Nessuno la usa per il paesaggio."
  },

  // --- BUS 12 "OUTLAND EXPRESS" -----------------------------------------------
  {
    id: "stz-mosslake",
    name: "MOSSLAKE HALT",
    lng: 17.8040, lat: 59.4280,
    district: "MOSSLAKE",
    blurb: "L'ultima fermata prima che le strade smettano letteralmente di esistere. Chi scende qui di solito non vuole essere seguito."
  },
  {
    id: "stz-custodian",
    name: "THE CUSTODIAN ARCHIVE",
    lng: 17.7020, lat: 59.3600,
    district: "THE CUSTODIAN",
    blurb: "Fermata senza insegne, come tutto il resto del distretto. Il bus si ferma comunque, per chi sa già dove scendere."
  },
  {
    id: "stz-inkwell",
    name: "INKWELL HEIGHTS STOP",
    lng: 17.7570, lat: 59.2360,
    district: "INKWELL™ HEIGHTS",
    blurb: "Fermata incastrata tra tipografie e officine clandestine. La rete qui è piena di nodi illegali quanto le strade di vicoli ciechi."
  },
  {
    id: "stz-great-spill",
    name: "THE GREAT SPILL EDGE",
    lng: 18.0430, lat: 59.1980,
    district: "THE GREAT SPILL",
    blurb: "Capolinea sud della Outland Express, ai bordi di una contaminazione mai davvero chiarita. Gli autisti fanno a turni per non finirci troppo spesso."
  },

  // --- Distretti finora scoperti: nuove stazioni ------------------------------
  {
    id: "stz-space",
    name: "SPACE ELEVATOR TERMINUS",
    lng: 18.02957, lat: 59.36939,
    district: "SPACE",
    blurb: "Ultima fermata prima degli ascensori orbitali. Il tornello legge il credito sul tuo conto prima ancora di leggere il biglietto: se non basta per l'ascensore, la maglev per te si ferma comunque qui."
  },
  {
    id: "stz-barnyard",
    name: "BARNYARD FIELDS SHRINE",
    lng: 18.085335, lat: 59.340571,
    district: "BARNYARD FIELDS",
    blurb: "Pensilina coperta di simboli che le SecCorps preferirebbero ignorare. Gli Heirs of Kergoz la usano come punto di raccolta prima delle liturgie nei campi anneriti poco distanti."
  },
  {
    id: "stz-aquaculture",
    name: "AQUACULTURE CAGE MAZE PIER",
    lng: 18.24330, lat: 59.3360,
    district: "AQUACULTURE CAGE MAZE",
    blurb: "Banchina sospesa sopra le vasche industriali. L'odore di pesce e biomassa sale fin quassù, mescolato ai fumi degli impianti chimici poco più a ovest."
  },
  {
    id: "stz-dreams-kaytell",
    name: "DREAMS BY KAYTELL PROMENADE",
    lng: 18.36721, lat: 59.21145,
    district: "DREAMS BY KAYTELL™",
    blurb: "Capolinea decorato con gli stessi slogan scoloriti che tappezzano il quartiere. La promenade promessa nei rendering non è mai stata costruita: resta solo il nome sulla pensilina."
  },

  // --- BUS 21 "PERIMETRO" ------------------------------------------------------
  {
    id: "stz-airport",
    name: "AIRPORT SHUTTLE HUB",
    lng: 17.9440, lat: 59.3540,
    district: "AIRPORT",
    blurb: "Navetta diretta ai terminal, per chi ha un biglietto e non ha comunque la certezza di volare davvero."
  },
  {
    id: "stz-edges",
    name: "EDGES CHECKPOINT",
    lng: 18.0780, lat: 59.3990,
    district: "EDGES",
    blurb: "Fermata al cancello di Cy Golf Village. Il bus che entra è pattugliato, quello che esce anche di più."
  },
  {
    id: "stz-perch-park",
    name: "PERCH PARK STOP",
    lng: 18.1080, lat: 59.3840,
    district: "PERCH PRODUCTIVITY PARK™",
    blurb: "Fermata cronometrata come tutto il resto del distretto: un cartello ricorda quanti secondi di produttività sono stati persi aspettando."
  },
  {
    id: "stz-blackfield",
    name: "BLACKFIELD HALT",
    lng: 18.0270, lat: 59.4540,
    district: "BLACKFIELD",
    blurb: "Capolinea nord della Perimetro, tra campi bruciati e terreni industriali dismessi. Il bus arriva vuoto e riparte quasi altrettanto vuoto."
  }
];

const TRANSIT_LINES = [
  {
    id: "linea-rossa",
    name: "MAGLEV — LINEA SANGUE",
    color: "#c8102e",
    type: "monorail",
    stations: [
      "stz-borghold", "stz-svarta", "stz-north-central",
      "stz-south-central", "stz-the-arcs", "stz-happy-town", "stz-crown-island"
    ]
  },
  {
    id: "linea-verde",
    name: "MAGLEV — LINEA OSSIDO",
    color: "#1FD400",
    type: "monorail",
    stations: [
      "stz-ports", "stz-paradise-spire", "stz-burnchurch",
      "stz-lower-walds", "stz-optima-depths"
    ]
  },
  {
    id: "linea-blu",
    name: "MAGLEV — LINEA NEON",
    color: "#00fff2",
    type: "monorail",
    stations: [
      "stz-lilypond", "stz-bigmosse", "stz-svarta", "stz-north-central",
      "stz-mosscroft", "stz-vertex-nova", "stz-evergreen-bay"
    ]
  },
  {
    id: "linea-ambra",
    name: "MAGLEV — LINEA AMBRA",
    color: "#e8a23a",
    type: "monorail",
    stations: [
      "stz-airport", "stz-space", "stz-barnyard", "stz-ports",
      "stz-vertex-nova", "stz-aquaculture", "stz-quay47"
    ]
  },
  {
    id: "linea-spettro",
    name: "MAGLEV — LINEA SPETTRO",
    color: "#a83cff",
    type: "monorail",
    stations: [
      "stz-crown-island", "stz-happy-town",
      "stz-lower-walds", "stz-great-spill", "stz-optima-depths"
    ]
  },
  {
    id: "bus-33",
    name: "BUS 33 — SPACE LINK",
    color: "#ff8cf1",
    type: "bus",
    stations: ["stz-airport", "stz-space", "stz-barnyard", "stz-north-central", "stz-airport"]
  },
  {
    id: "bus-45",
    name: "BUS 45 — AQUACULTURE LOOP",
    color: "#38bdf8",
    type: "bus",
    stations: ["stz-vertex-nova", "stz-aquaculture", "stz-quay47", "stz-prophet-park"]
  },
  {
    id: "bus-50",
    name: "BUS 50 — KAYTELL SHUTTLE",
    color: "#ff2ee6",
    type: "bus",
    stations: ["stz-dreams-kaytell", "stz-quay47", "stz-cot-square"]
  },
  {
    id: "bus-07",
    name: "BUS 07 — CROSSTOWN",
    color: "#e8c93a",
    type: "bus",
    stations: [
      "stz-laketon", "stz-galgbacken", "stz-quay47",
      "stz-prophet-park", "stz-low-meadow", "stz-cot-square"
    ]
  },
  {
    id: "bus-12",
    name: "BUS 12 — OUTLAND EXPRESS",
    color: "#8c3a7a",
    type: "bus",
    stations: [
      "stz-mosslake", "stz-custodian",
      "stz-inkwell", "stz-optima-depths", "stz-great-spill"
    ]
  },
  {
    id: "bus-21",
    name: "BUS 21 — PERIMETRO",
    color: "#b9b6b0",
    type: "bus",
    stations: [
      "stz-airport", "stz-edges", "stz-perch-park", "stz-blackfield"
    ]
  }
];
