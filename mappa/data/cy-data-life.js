/* =========================================================================
   CY — DATI: VITA DI CITTÀ (pedoni, traffico, droni, elicotteri)
   Configurazione e tavolozze usate dal modulo "VITA DI CITTÀ" in index.html.
   Le entità compaiono solo da zoom ravvicinato (minZoom) e si muovono lungo
   le strade vere della mappa. Tutti i numeri qui sotto si possono ritoccare.
   Caricare PRIMA della logica di index.html (come gli altri cy-data-*.js).
   ========================================================================= */

const CITY_LIFE = {
  // --- visibilità / prestazioni ---------------------------------------
  minZoom: 17,          // sotto questo zoom (con una piccola dissolvenza) la vita sparisce e la simulazione si ferma
  hotkeys: { pause: 'KeyP', hide: 'KeyH' },   // P = ferma/riprendi, H = nascondi/mostra (codici di KeyboardEvent.code)
  fps: 30,              // aggiornamenti al secondo della geometria 3D (più alto = più fluido, più pesante)
  netRadius: 800,       // metri attorno al centro schermo di cui si legge la rete stradale
  view: { min: 140, max: 520, factor: 0.9 },   // raggio (m) in cui vivono le entità: ~ metà schermo, limitato tra min e max

  // --- quante entità (su mobile vengono dimezzate) ---------------------
  cars: 110,   carsPerKm: 22,    // massimo, e densità massima per km di strada percorribile in auto nel raggio
  peds: 230,   pedsPerKm: 38,    // idem per i pedoni (conta i due marciapiedi)
  drones: 16,                    // droni a bassa quota che seguono le strade

  // --- elicotteri ------------------------------------------------------
  helicopters: {
    max: 2,                          // contemporanei
    minGapMs: 9000, maxGapMs: 26000, // pausa casuale tra un passaggio e l'altro
    altitude: [140, 280],            // metri
    speed: [65, 110],                // m/s (sfrecciano)
    escortChance: 0.25,              // probabilità che ne arrivi un secondo in coppia
    callsigns: ['SEC-AIR', 'UCS-WING', 'TRAUMA', 'NEWS-CY', 'ACGS-AIR']
  },

  // --- nickname sopra le teste ----------------------------------------
  labels: { minZoom: 17.4, max: 36, radiusM: 170 },  // solo le entità più vicine al centro, entro radiusM metri

  // --- dimensioni (le altezze dei palazzi sono già moltiplicate x4: ingrandiamo un po' anche le entità) ---
  sizeXY: 0.5,
  sizeZ: 0.5,
  sidewalk: 1.8,        // distanza (m) del marciapiede dal bordo della carreggiata

  // --- dove NON c'è vita (zone di quarantena, ecc.) -------------------
  noLifeKinds: ['car'],                           // cosa NON può stare nelle zone qui sotto: 'car' (auto/furgoni/bus), 'ped' (pedoni), 'drone'. Ora G0 è vietato solo alle auto
  noLifeWalls: ['MURO NORTH CENTRAL / EDGES'],   // nomi in WALL_DEFS: l'area racchiusa dal muro è vuota (G0)
  noLifeMarginM: 200,                             // fascia di rispetto (m) anche FUORI dal muro, per i tipi in noLifeKinds (copre anche CY_SANITAZION HQ)
  noLifeCircles: [],                              // es. { lng:18.0663, lat:59.2652, r:1500 }
  noPedCircles: [{ lng: 18.04103, lat: 59.33949, r: 700 }],   // i pedoni non entrano nel cratere/lago di G0 (valgono sempre, a prescindere da noLifeKinds)

  // zone dove lo stile rimuove i palazzi (blast del cratere di G0): lì non contano come ostacoli per l'occlusione
  ignoreBuildingsCircles: [{ lng: 18.04103, lat: 59.33949, r: 600 }],

  // --- strade ------------------------------------------------------------
  allClasses: ['motorway','trunk','primary','secondary','tertiary','minor','service','path'],
  carClasses: ['motorway','trunk','primary','secondary','tertiary','minor','service'],
  pedClasses: ['primary','secondary','tertiary','minor','service','path'],
  roadHalfWidth: { motorway: 9, trunk: 8, primary: 7, secondary: 6, tertiary: 5, minor: 4, service: 3, path: 0 },
  carSpeed: { motorway: 22, trunk: 19, primary: 14, secondary: 12, tertiary: 10, minor: 8, service: 5 },   // m/s

  // --- veicoli (misure in metri reali, poi scalate da sizeXY/sizeZ) -------
  vehicleTypes: [
    { id: 'car', w: 0.78, len: 4.2, wid: 1.85, h: 1.25, cabLen: 2.3, cabOff: -0.25, cabH: 0.6, cabColor: '#15181d' },
    { id: 'van', w: 0.14, len: 5.4, wid: 2.1,  h: 1.9,  cabLen: 3.4, cabOff: -0.6,  cabH: 0.8, cabColor: '#1b2128' },
    { id: 'bus', w: 0.08, len: 10.5, wid: 2.5, h: 2.7,  cabLen: 9.4, cabOff: 0,     cabH: 0.5, cabColor: '#bfe6ff',
      classes: ['primary','secondary','tertiary'], colors: ['#c8102e','#e8c93a','#8c3a7a'] }
  ],

  // --- tavolozze -----------------------------------------------------------
  carColors: ['#1c1f26','#2b2f3a','#3b1320','#102a3a','#4a4f5a','#5a2a2a','#d8d4cc','#1f3a2c','#6b5a1f','#3a2a4a'],
  neon: ['#00fff2','#ff2ee6','#e8c93a','#7cff4a','#ff4a4a','#8a5cff'],
  pedClothes: ['#2a2d36','#3a2a3e','#1d3a3a','#4a3b2a','#5a1f2a','#2d4a2d','#6b6b72','#1a1a1a','#8c3a7a','#c8102e'],
  skin: ['#d9b08c','#b98560','#8d5a3c','#f0cdb0','#5e3b26','#c99a74'],

  // parole per i nickname: @parola_parola_0000
  nickWords: ['neo','kira','jax','mox','zed','nyx','viff','fl4s','rex','vex','sly','dex','ono','lux','tek','ryo','kodo','mira','vlad','sasha',
    'rusty','glitch','ghost','static','cold','mad','dead','lazy','dirty','blind','toxic','neon','chrome','cheap','sad','lucky','loud','slick','tired','broke',
    'wolf','rat','blade','wire','crow','moth','pixel','spark','cat','snake','fox','noodle','junk','scrap','hex','byte','sprout','jackal','vandal','hound']
};