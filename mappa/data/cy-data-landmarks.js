/* =========================================================================
   CY — DATI: LANDMARK BUILDINGS (3D)
   Incolla qui, byte-per-byte, l'array che nella logica originale veniva
   assegnato DENTRO addLandmarkLayer() a `landmarkFeatures = [ ... ]`.
   Qui va rinominato in LANDMARK_FEATURES (la logica ora fa
   `landmarkFeatures = LANDMARK_FEATURES;`).
   Ogni voce è una Feature GeoJSON di tipo Polygon con properties
   { name, height, base, color, blurb, street?, number?, subAddress?, address? }.
   ========================================================================= */

const LANDMARK_FEATURES  = [
    {
      "type": "Feature",
      "properties": {
        "name": "@dr_neo101",
        "height": 20,
        "base": 0,
        "street": "BLADE AVENUE",
        "number": 101,
        "subAddress": "a3_832",
        "color": "#e8c93a",
        "address": "BLADE AVENUE, #101",
        "blurb": "Il covo/laboratorio del ripperdoc Dr Neo è nascosto in una porzione di un enorme edificio verticale, tra centinaia di appartamenti e attività. Sorvegliato quanto basta per scoraggiare i curiosi: meglio citofonare. Sul retro c'è un piccolo accesso di servizio."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.88993,
              59.3435097
            ],
            [
              17.8900511,
              59.343619
            ],
            [
              17.8886862,
              59.3439359
            ],
            [
              17.8886431,
              59.3438967
            ],
            [
              17.8886892,
              59.3438835
            ],
            [
              17.8887977,
              59.3438558
            ],
            [
              17.8888057,
              59.3438005
            ],
            [
              17.8887409,
              59.343791
            ],
            [
              17.8886526,
              59.343784
            ],
            [
              17.888624,
              59.3438211
            ],
            [
              17.8886547,
              59.3438521
            ],
            [
              17.8886086,
              59.3438653
            ],
            [
              17.8883234,
              59.3436056
            ],
            [
              17.889069,
              59.3436259
            ],
            [
              17.8894094,
              59.3436005
            ],
            [
              17.8897484,
              59.3435564
            ],
            [
              17.88993,
              59.3435097
            ]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "@dr_neo101",
        "height": 100,
        "base": 0,
        "street": "BLADE AVENUE",
        "number": 101,
        "subAddress": "a3_832",
        "color": "#e8c93a",
        "blurb": "Il covo/laboratorio del ripperdoc Dr Neo è nascosto in una porzione di un enorme edificio verticale, tra centinaia di appartamenti e attività. Sorvegliato quanto basta per scoraggiare i curiosi: meglio citofonare. Sul retro c'è un piccolo accesso di servizio."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8899299,
              59.3435097
            ],
            [
              17.8900511,
              59.343619
            ],
            [
              17.8890146,
              59.3438596
            ],
            [
              17.889069,
              59.3436259
            ],
            [
              17.8894094,
              59.3436005
            ],
            [
              17.8897485,
              59.3435564
            ],
            [
              17.8899299,
              59.3435097
            ]]]
      }
    },    {
      "type": "Feature",
      "properties": {
        "name": "null",
        "height": 0.3,
        "base": 0,
        "color": "#00000a",
        "blurb": "E tu che cazzo ci fai qui? Un vecchio pesca dal molo, immobile da troppo tempo. É un live feed, l'acqua é cristallina, Il sole splende. Lui non ti guarda. Non serve. Guadagni d2 glitch al giorno.<br><br>CONTATTA IL DM."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8657755,
              58.7378165
            ],
            [
              17.8657587,
              58.7378435
            ],
            [
              17.8657542,
              58.7378597
            ],
            [
              17.8658711,
              58.7378356
            ],
            [
              17.8658508,
              58.7378063
            ],
            [
              17.8658872,
              58.7377986
            ],
            [
              17.8658889,
              58.737801
            ],
            [
              17.8658579,
              58.7378074
            ],
            [
              17.8658776,
              58.7378342
            ],
            [
              17.8659209,
              58.737824
            ],
            [
              17.8659414,
              58.7378465
            ],
            [
              17.8657047,
              58.7378901
            ],
            [
              17.8657129,
              58.7378822
            ],
            [
              17.8657162,
              58.7378785
            ],
            [
              17.8657146,
              58.737877
            ],
            [
              17.8657134,
              58.7378758
            ],
            [
              17.8657078,
              58.737874
            ],
            [
              17.8656961,
              58.7378748
            ],
            [
              17.8656699,
              58.737838
            ],
            [
              17.8657755,
              58.7378165
            ]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "null",
        "height": 2,
        "base": 0,
        "color": "#00000a",
        "blurb": "E tu che cazzo ci fai qui? Un vecchio pesca dal molo, immobile da troppo tempo. É un live feed e l'acqua é limpida. Non ti guarda. Non serve. Guadagni d2 glitch al giorno.<br>CONTATTA IL DM."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8657405,
              58.7378612
            ],
            [
              17.8657443,
              58.7378683
            ],
            [
              17.8657582,
              58.7378626
            ],
            [
              17.8657508,
              58.737858
            ],
            [
              17.8657425,
              58.7378528
            ],
            [
              17.865757,
              58.7378506
            ],
            [
              17.8657691,
              58.7378503
            ],
            [
              17.8657753,
              58.737852
            ],
            [
              17.8657822,
              58.7378547
            ],
            [
              17.865789,
              58.7378568
            ],
            [
              17.8657651,
              58.7378667
            ],
            [
              17.8657462,
              58.7378745
            ],
            [
              17.8657047,
              58.7378901
            ],
            [
              17.8657129,
              58.7378822
            ],
            [
              17.8657162,
              58.7378785
            ],
            [
              17.8657146,
              58.737877
            ],
            [
              17.8657134,
              58.7378758
            ],
            [
              17.8657078,
              58.737874
            ],
            [
              17.8656961,
              58.7378748
            ],
            [
              17.8657258,
              58.7378599
            ],
            [
              17.8657405,
              58.7378612
            ]]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "The Night Owl Bar",
        "height": 5,
        "base": 0,
        "color": "#8cd406",
        "address": "PHANTOM YARD, #326",
        "blurb": "<img src=\"img/night-owl.jpg\" alt=\"Mia Immagine\">"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8776087,
              59.347994
            ],
            [
              17.8776998,
              59.3479591
            ],
            [
              17.8774747,
              59.347808
            ],
            [
              17.8773841,
              59.3478442
            ],
            [
              17.8776087,
              59.347994
            ]]]
      }
    },
    {
      type: "Feature",
      properties: { name: "La Gloriosa Chiesa della Divina Misericordia™", height: 15, base: 0, color: "#859c03",
        "street": "NEURALNET™ TRENCH",
        "number": 1441,
        "subAddress": "a3_832",
        "color": "#e8c93a",
        "address": "NEURALNET™ TRENCH, #1441",
        blurb: "<img src=\"img/chiesa_svarta.jpg\" alt=\"Mia Immagine\">" },
      geometry: {
        type: "Polygon",
        "coordinates": [
          [
            [
              17.8755119,
              59.358642
            ],
            [
              17.8754029,
              59.358702
            ],
            [
              17.8750896,
              59.3585498
            ],
            [
              17.8750337,
              59.3584877
            ],
            [
              17.8748599,
              59.3584021
            ],
            [
              17.875017,
              59.3583171
            ],
            [
              17.8753124,
              59.3584589
            ],
            [
              17.8753455,
              59.3585645
            ],
            [
              17.8755119,
              59.358642
            ]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Arca", height: 700, base: 0, color: "#038207",
        blurb: "Arcologia." },
      geometry: {
        type: "Polygon",
        "coordinates": [[
                    [17.9141979, 59.3081772],
                    [17.9169664, 59.3081772],
                    [17.9169664, 59.3066870],
                    [17.9141979, 59.3066870],
                    [17.9141979, 59.3081772]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Arca", height: 700, base: 0, color: "#038207",
        blurb: "Arcologia." },
      geometry: {
        type: "Polygon",
        "coordinates": [[
                    [17.9241979, 59.3081772],
                    [17.9269664, 59.3081772],
                    [17.9269664, 59.3066870],
                    [17.9241979, 59.3066870],
                    [17.9241979, 59.3081772]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Arca", height: 700, base: 0, color: "#038207",
        blurb: "Arcologia." },
      geometry: {
        type: "Polygon",
        "coordinates": [[
                    [17.9191979, 59.3081772],
                    [17.9219664, 59.3081772],
                    [17.9219664, 59.3066870],
                    [17.9191979, 59.3066870],
                    [17.9191979, 59.3081772]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Floating Hive", height: 350, base: 0, color: "#038207",
        blurb: "L'arcologia dove ha sede la  Cynergy Water & Power Co." },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [17.9007607,59.3082817],[17.900639,59.3083276],[17.9004474,59.3083438],
          [17.9000716,59.3083082],[17.8999147,59.3083236],[17.8995965,59.3082452],
          [17.8993074,59.3082915],[17.8991212,59.3083247],[17.8989728,59.3084048],
          [17.8990813,59.3084885],[17.8994874,59.308592],[17.8996933,59.3086819],
          [17.8997813,59.3087698],[17.8997176,59.3088727],[17.8997424,59.3090058],
          [17.8998267,59.3091295],[17.9000876,59.3092886],[17.9003362,59.3094945],
          [17.9010773,59.3098077],[17.9015563,59.3098942],[17.9021935,59.3100074],
          [17.9032282,59.3101262],[17.9043367,59.3101971],[17.9055421,59.3101349],
          [17.9060018,59.3100073],[17.9061913,59.3099853],[17.906216,59.309909],
          [17.9064362,59.3098035],[17.9063479,59.3096289],[17.9063093,59.3095629],
          [17.9060534,59.309429],[17.9059782,59.3094001],[17.9058678,59.3091528],
          [17.905631,59.3089694],[17.905383,59.3088109],[17.9053231,59.308695],
          [17.9053957,59.3085638],[17.9053617,59.3084008],[17.9052425,59.3082786],
          [17.9051501,59.3080786],[17.9051033,59.3079083],[17.9051019,59.3078195],
          [17.9048434,59.3076228],[17.9046758,59.3075141],[17.9046318,59.3074625],
          [17.9046535,59.3073233],[17.9046355,59.3071631],[17.9044178,59.3071039],
          [17.9041545,59.3070933],[17.9036642,59.3072608],[17.9034991,59.3073524],
          [17.9033329,59.3074021],[17.9031155,59.3074124],[17.9026897,59.3074544],
          [17.9027232,59.3074985],[17.9026178,59.3075254],[17.9017803,59.3078171],
          [17.9015793,59.3078677],[17.9019716,59.3083346],[17.9019983,59.3086183],
          [17.9016194,59.3087166],[17.9011116,59.3087302],[17.9006521,59.3086287],
          [17.9007607,59.3082817]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Floating Hive", height: 750, base: 0, color: "#038207",
        blurb: "L'arcologia dove ha sede la  Cynergy Water & Power Co." },
      geometry: {
        type: "Polygon",
        "coordinates": [
          [
            [
              17.8999147,
              59.3083236
            ],
            [
              17.8995965,
              59.3082452
            ],
            [
              17.8993074,
              59.3082915
            ],
            [
              17.8991212,
              59.3083247
            ],
            [
              17.8989728,
              59.3084048
            ],
            [
              17.8990813,
              59.3084885
            ],
            [
              17.8994874,
              59.308592
            ],
            [
              17.8996933,
              59.3086819
            ],
            [
              17.8999834,
              59.3086579
            ],
            [
              17.8999147,
              59.3083236
            ]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Floating Hive", height: 450, base: 0, color: "#038207",
        blurb: "L'arcologia dove ha sede la  Cynergy Water & Power Co." },
      geometry: {
        type: "Polygon",
         "coordinates": [
          [
            [
              17.9007607,
              59.3082817
            ],
            [
              17.900639,
              59.3083276
            ],
            [
              17.9004474,
              59.3083438
            ],
            [
              17.9000716,
              59.3083082
            ],
            [
              17.8999147,
              59.3083236
            ],
            [
              17.8995965,
              59.3082452
            ],
            [
              17.8993074,
              59.3082915
            ],
            [
              17.8991212,
              59.3083247
            ],
            [
              17.8989728,
              59.3084048
            ],
            [
              17.8990813,
              59.3084885
            ],
            [
              17.8994874,
              59.308592
            ],
            [
              17.8996933,
              59.3086819
            ],
            [
              17.8997813,
              59.3087698
            ],
            [
              17.8997424,
              59.3090058
            ],
            [
              17.8998267,
              59.3091295
            ],
            [
              17.9000876,
              59.3092886
            ],
            [
              17.9003362,
              59.3094945
            ],
            [
              17.9004621,
              59.3092276
            ],
            [
              17.9005801,
              59.3089539
            ],
            [
              17.9006033,
              59.3088568
            ],
            [
              17.9006239,
              59.3087504
            ],
            [
              17.9006521,
              59.3086287
            ],
            [
              17.9007607,
              59.3082817
            ]
        ]]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 01",
        "height": 117.3,
        "base": 100,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9009543,
              59.3082002
            ],
            [
              17.9011178,
              59.3083317
            ],
            [
              17.90086,
              59.3084152
            ],
            [
              17.9006965,
              59.3082836
            ],
            [
              17.9009543,
              59.3082002
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 02",
        "height": 67.0,
        "base": 50,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8999789,
              59.3081403
            ],
            [
              17.9001302,
              59.3082721
            ],
            [
              17.8998721,
              59.3083493
            ],
            [
              17.8997209,
              59.3082176
            ],
            [
              17.8999789,
              59.3081403
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 03",
        "height": 56.2,
        "base": 40,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8988606,
              59.3082251
            ],
            [
              17.8991194,
              59.3082868
            ],
            [
              17.8989985,
              59.308419
            ],
            [
              17.8987397,
              59.3083573
            ],
            [
              17.8988606,
              59.3082251
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 04",
        "height": 126.0,
        "base": 100,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8994457,
              59.3085365
            ],
            [
              17.8994488,
              59.3087697
            ],
            [
              17.898992,
              59.3087713
            ],
            [
              17.8989889,
              59.3085381
            ],
            [
              17.8994457,
              59.3085365
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 05",
        "height": 223.1,
        "base": 200,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8996231,
              59.3086905
            ],
            [
              17.8998034,
              59.3088767
            ],
            [
              17.8994386,
              59.3089688
            ],
            [
              17.8992583,
              59.3087825
            ],
            [
              17.8996231,
              59.3086905
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 06",
        "height": 13.7,
        "base": 0,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.8998673,
              59.3092136
            ],
            [
              17.9000925,
              59.3092569
            ],
            [
              17.9000075,
              59.3093719
            ],
            [
              17.8997824,
              59.3093285
            ],
            [
              17.8998673,
              59.3092136
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 07",
        "height": 313.2,
        "base": 300,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.900175,
              59.3094813
            ],
            [
              17.900406,
              59.3094944
            ],
            [
              17.9003804,
              59.3096122
            ],
            [
              17.9001494,
              59.3095992
            ],
            [
              17.900175,
              59.3094813
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 08",
        "height": 71.8,
        "base": 50,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9010259,
              59.3097731
            ],
            [
              17.9013361,
              59.3098883
            ],
            [
              17.9011104,
              59.3100466
            ],
            [
              17.9008003,
              59.3099315
            ],
            [
              17.9010259,
              59.3097731
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 09",
        "height": 123.2,
        "base": 100,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9018448,
              59.3099198
            ],
            [
              17.9021807,
              59.3100389
            ],
            [
              17.9019474,
              59.3102104
            ],
            [
              17.9016115,
              59.3100913
            ],
            [
              17.9018448,
              59.3099198
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 10",
        "height": 225.2,
        "base": 200,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9029545,
              59.3100552
            ],
            [
              17.90306,
              59.3102755
            ],
            [
              17.9026284,
              59.3103294
            ],
            [
              17.9025229,
              59.3101091
            ],
            [
              17.9029545,
              59.3100552
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 11",
        "height": 88.0,
        "base": 80,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9031933,
              59.3101174
            ],
            [
              17.9033267,
              59.3101406
            ],
            [
              17.9032811,
              59.3102087
            ],
            [
              17.9031477,
              59.3101854
            ],
            [
              17.9031933,
              59.3101174
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 12",
        "height": 44.4,
        "base": 20,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9041307,
              59.3101405
            ],
            [
              17.9044481,
              59.3102879
            ],
            [
              17.9041593,
              59.3104499
            ],
            [
              17.9038418,
              59.3103025
            ],
            [
              17.9041307,
              59.3101405
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 13",
        "height": 85.6,
        "base": 60,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9048317,
              59.3101239
            ],
            [
              17.905198,
              59.3102586
            ],
            [
              17.9049341,
              59.3104455
            ],
            [
              17.9045679,
              59.3103108
            ],
            [
              17.9048317,
              59.3101239
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 14",
        "height": 89.3,
        "base": 80,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9060576,
              59.3099885
            ],
            [
              17.9061477,
              59.3100584
            ],
            [
              17.9060108,
              59.3101044
            ],
            [
              17.9059207,
              59.3100345
            ],
            [
              17.9060576,
              59.3099885
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 15",
        "height": 222.0,
        "base": 200,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9064983,
              59.3095916
            ],
            [
              17.9068515,
              59.3096729
            ],
            [
              17.9066921,
              59.3098531
            ],
            [
              17.906339,
              59.3097718
            ],
            [
              17.9064983,
              59.3095916
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 16",
        "height": 9.6,
        "base": 0,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9062908,
              59.3094492
            ],
            [
              17.9064367,
              59.309492
            ],
            [
              17.9063527,
              59.3095665
            ],
            [
              17.9062067,
              59.3095236
            ],
            [
              17.9062908,
              59.3094492
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 17",
        "height": 325.4,
        "base": 300,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9059111,
              59.3087384
            ],
            [
              17.9060766,
              59.3089499
            ],
            [
              17.9056622,
              59.3090344
            ],
            [
              17.9054967,
              59.3088229
            ],
            [
              17.9059111,
              59.3087384
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 18",
        "height": 110.1,
        "base": 100,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9054147,
              59.3085491
            ],
            [
              17.9055797,
              59.3085835
            ],
            [
              17.9055125,
              59.3086677
            ],
            [
              17.9053475,
              59.3086333
            ],
            [
              17.9054147,
              59.3085491
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 19",
        "height": 99.8,
        "base": 90,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9052498,
              59.3082189
            ],
            [
              17.9054218,
              59.3082272
            ],
            [
              17.9054056,
              59.308315
            ],
            [
              17.9052335,
              59.3083067
            ],
            [
              17.9052498,
              59.3082189
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 20",
        "height": 222.3,
        "base": 200,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9051648,
              59.3077656
            ],
            [
              17.9055429,
              59.3078209
            ],
            [
              17.9054345,
              59.3080139
            ],
            [
              17.9050565,
              59.3079586
            ],
            [
              17.9051648,
              59.3077656
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 21",
        "height": 118.1,
        "base": 100,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.904985,
              59.3074846
            ],
            [
              17.9052276,
              59.3075895
            ],
            [
              17.9050221,
              59.3077134
            ],
            [
              17.9047795,
              59.3076085
            ],
            [
              17.904985,
              59.3074846
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 22",
        "height": 141.4,
        "base": 130,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9048031,
              59.3072387
            ],
            [
              17.9048853,
              59.3073324
            ],
            [
              17.9047017,
              59.3073744
            ],
            [
              17.9046194,
              59.3072806
            ],
            [
              17.9048031,
              59.3072387
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 23",
        "height": 80.4,
        "base": 70,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9038766,
              59.307078
            ],
            [
              17.9039734,
              59.3071568
            ],
            [
              17.9038189,
              59.3072062
            ],
            [
              17.9037221,
              59.3071274
            ],
            [
              17.9038766,
              59.307078
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 24",
        "height": 40.1,
        "base": 30,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9034205,
              59.307255
            ],
            [
              17.9035608,
              59.3073107
            ],
            [
              17.9034517,
              59.3073823
            ],
            [
              17.9033114,
              59.3073266
            ],
            [
              17.9034205,
              59.307255
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 25",
        "height": 141.8,
        "base": 130,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9025638,
              59.307434
            ],
            [
              17.9027536,
              59.3074777
            ],
            [
              17.902668,
              59.3075746
            ],
            [
              17.9024782,
              59.3075309
            ],
            [
              17.9025638,
              59.307434
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 26",
        "height": 225.5,
        "base": 200,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9020611,
              59.3074876
            ],
            [
              17.9021974,
              59.3077057
            ],
            [
              17.9017702,
              59.3077752
            ],
            [
              17.9016339,
              59.3075572
            ],
            [
              17.9020611,
              59.3074876
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 27",
        "height": 163.5,
        "base": 150,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9016256,
              59.3078925
            ],
            [
              17.9016682,
              59.3080115
            ],
            [
              17.9014349,
              59.3080333
            ],
            [
              17.9013923,
              59.3079142
            ],
            [
              17.9016256,
              59.3078925
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 28",
        "height": 31.8,
        "base": 20,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9018541,
              59.3083742
            ],
            [
              17.9020231,
              59.3084357
            ],
            [
              17.9019026,
              59.3085219
            ],
            [
              17.9017336,
              59.3084604
            ],
            [
              17.9018541,
              59.3083742
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 29",
        "height": 23.4,
        "base": 0,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9016366,
              59.3084679
            ],
            [
              17.901856,
              59.3086455
            ],
            [
              17.901508,
              59.3087575
            ],
            [
              17.9012885,
              59.3085799
            ],
            [
              17.9016366,
              59.3084679
            ]
          ]
        ]
      }
    },
    {
      "type": "Feature",
      "properties": {
        "name": "Hub Vagante 30",
        "height": 9.8,
        "base": 0,
        "color": "#038207",
        "blurb": "Unita' cubica atavistica del cluster Floating Hive, in perenne deriva lungo il perimetro."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              17.9008332,
              59.3085557
            ],
            [
              17.9008361,
              59.3086438
            ],
            [
              17.9006635,
              59.3086452
            ],
            [
              17.9006606,
              59.3085572
            ],
            [
              17.9008332,
              59.3085557
            ]
          ]
        ]
      }
    },
    {
      type: "Feature",
      properties: { name: "Undersjön", height: 5, base: 0, color: "#080707",
        blurb: "Un altare al consumismo, sotto forma di un vasto parco commerciale chiamato Undersjön, è in costruzione permanente sotto il Lago Gravel, separando il nord e il sud di Central.." },
      geometry: {
        type: "Polygon",
        "coordinates": [
                  [
                    [
                      17.9608895,
                      59.3135082
                    ],
                    [
                      17.9696576,
                      59.3135082
                    ],
                    [
                      17.9696576,
                      59.3095812
                    ],
                    [
                      17.9653295,
                      59.3095876
                    ],
                    [
                      17.9608895,
                      59.3095812
                    ],
                    [
                      17.9608895,
                      59.3135082
                    ]
                ]]
      }
    },
    {
      type: "Aquaculture Cage Maze",
      properties: { name: "Undersjön", height: 5, base: 0, color: "#b4bf1b",
        blurb: "Dedalo di allevamenti di cibo commestibile e non commestibile." },
      geometry: {
        type: "Polygon",
        "coordinates": [
          [
            [
              18.201400927858714,
              59.3385812
            ],
            [
              18.2124592,
              59.3385812
            ],
            [
              18.2124592,
              59.33500700878196
            ],
            [
              18.201400927858714,
              59.33500700878196
            ],
            [
              18.201400927858714,
              59.3385812
            ]
                ]]
      }
    },
    {
      type: "Feature",
      properties: { name: "Floating Hive", height: 700, base: 0, color: "#038207",
        blurb: "L'arcologia dove ha sede la  Cynergy Water & Power Co." },
      geometry: {
        type: "Polygon",
        "coordinates": [
          [
            [
              17.902127410889506,
              59.30799503756222
            ],
            [
              17.904806073507046,
              59.308183481305605
            ],
            [
              17.904439358910594,
              59.30954152130536
            ],
            [
              17.901760696291603,
              59.309353085087366
            ],
            [
              17.902127410889506,
              59.30799503756222
            ]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { 
              name: "Edificio #1: officina di @chopshop__1147", 
              height: 0.3, 
              base: 0, 
              color: "#1FD400",
              street: "DRIFT TRENCH",
              number: 1,
              subAddress: "a0_1",
              blurb: "Un'discarica clandestina dove veicoli e cyberware rubati cambiano identità nel giro di una notte." },
      geometry: {
        type: "Polygon",
        coordinates: [[
          [17.873871,59.3506892],[17.8744383,59.3503742],[17.8745645,59.3504559],
          [17.8746099,59.3505009],[17.8748878,59.3506435],[17.8745497,59.3507996],
          [17.8742476,59.3508262],[17.8741208,59.3507603],[17.8741205,59.3507612],
          [17.873871,59.3506892]
        ]]
      }
    },
    {
      type: "Feature",
      properties: { 
              name: "Edificio #1: officina di @chopshop__1147", 
              height: 1.5, 
              base: 0, 
              color: "#1FD400",
              street: "DRIFT TRENCH, #1",
              number: 1,
              subAddress: "a0_1",
              blurb: "Un'discarica clandestina dove veicoli e cyberware rubati cambiano identità nel giro di una notte." },
      geometry: {
        type: "Polygon",
        "coordinates": [
          [
            [
              17.87414596532841,
              59.35064705084352
            ],
            [
              17.874147783193024,
              59.35064705084352
            ],
            [
              17.874147783193024,
              59.35064705084352
            ],
            [
              17.87414596532841,
              59.35064705084352
            ],
            [
              17.8742526,
              59.3506778
            ],
            [
              17.8744247,
              59.3506672
            ],
            [
              17.8744316,
              59.350627
            ],
            [
              17.8743005,
              59.3505541
            ],
            [
              17.87414596532841,
              59.35064705084352
            ]
        ]]
      }
    }
  ];

