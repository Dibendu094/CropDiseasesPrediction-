"""
AgriCare AI — Disease info builder (v2, 91-class model)
=======================================================
Builds `disease_info.json` so that EVERY class in class_names.json has a
matching, farmer-friendly entry.

  • The 38 PlantVillage classes are preserved from disease_info.backup42.json.
  • ~53 new classes (Rice, Mango, Banana, Coffee, Cotton, Rose, Soybean,
    Sugarcane, Grape) are authored below.
  • Any class no longer present in class_names.json is dropped automatically
    (we only emit keys that appear in class_names.json).

Run:  python build_disease_info.py
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLASSES = os.path.join(BASE_DIR, 'class_names.json')
BACKUP = os.path.join(BASE_DIR, 'disease_info.backup42.json')
OUT = os.path.join(BASE_DIR, 'disease_info.json')

MILD_SUN = ("Early morning (6:00–9:00 AM) or evening after 4:00 PM, when sunlight "
            "is mild and there is little wind.")
NO_SPRAY = ("No spraying needed while the plant is healthy — do routine care during "
            "the cool morning hours.")
CHEMICAL_SAFETY = [
    "While spraying any chemical, wear a mask, gloves and full-sleeve clothes, and never spray against the wind.",
    "Keep children and animals away from sprayed plants, and do not harvest before the waiting period printed on the product label.",
    "Alternate between different chemical groups so the fungus/pest does not become resistant.",
]
HEALTHY_CARE = [
    "Keep watering even and at the base of the plant; avoid wetting the leaves.",
    "Add compost or well-rotted farmyard manure to keep the soil rich and alive.",
    "Scout the field weekly and remove any weak, yellowing or damaged leaves early.",
    "Spray Neem oil (5 ml/L) once every 10–15 days as a preventive shield.",
]

CROP_HINDI = {
    "Rice": "धान / चावल", "Soybean": "सोयाबीन", "Grape": "अंगूर", "Mango": "आम",
    "Banana": "केला", "Coffee": "कॉफ़ी", "Cotton": "कपास", "Rose": "गुलाब",
    "Sugarcane": "गन्ना",
}


def D(crop, disease, symptoms, cause, organic, chemical, prevent,
      affected=None, best=MILD_SUN, healthy=False, desc=""):
    """Compact constructor for a disease entry."""
    return {
        "crop": crop,
        "crop_hindi": CROP_HINDI.get(crop, ""),
        "disease": disease,
        "is_healthy": healthy,
        "description": desc,
        "cause": cause,
        "affected_parts": affected or ["Leaves"],
        "symptoms": symptoms,
        "organic_remedy": organic,
        "chemical_spray": chemical,
        "preventive_measures": prevent,
        "prevention": prevent,
        "best_time_to_spray": NO_SPRAY if healthy else best,
    }


def healthy_entry(crop, note):
    return D(crop, "Healthy",
             symptoms=[note], cause="", organic=HEALTHY_CARE, chemical=[],
             prevent=["Use certified, disease-free planting material.",
                      "Keep the field clean and remove old crop residue after harvest.",
                      "Scout weekly so any problem is caught early."],
             healthy=True, desc=f"The {crop.lower()} leaf looks healthy with no disease symptoms.")


# ── Per-crop fertilizer plans (name : dose + timing + benefit) ──────────────
CROP_FERTILIZERS = {
    "Rice": [
        {"name": "Urea (Nitrogen)", "purpose": "Apply in 3 splits (basal, tillering, panicle) — never all at once, as an over-dose invites blast and blight."},
        {"name": "Muriate of Potash (MOP)", "purpose": "Apply 15–20 kg per acre at tillering; hardens the plant against disease and lodging."},
        {"name": "Zinc Sulfate 21%", "purpose": "Apply 10 kg per acre in zinc-poor soils; prevents brown patches and stunting (khaira)."},
    ],
    "Soybean": [
        {"name": "DAP (Phosphorus)", "purpose": "Apply 50–60 kg per acre at sowing; builds strong roots and good nodules."},
        {"name": "Rhizobium Culture", "purpose": "Coat the seed before sowing; fixes free nitrogen from the air and cuts urea need."},
        {"name": "Sulphur (Bentonite)", "purpose": "Apply 8–10 kg per acre; boosts oil content and pod filling."},
    ],
    "Grape": [
        {"name": "Potassium Sulfate (SOP)", "purpose": "Apply 250–300 g per vine after fruit-set; improves berry sugar, colour and skin strength."},
        {"name": "Calcium Nitrate", "purpose": "Spray 4 g per litre during berry growth; firms the skin and lowers rot and cracking."},
        {"name": "Farmyard Manure (Compost)", "purpose": "Apply 10–15 kg per vine before pruning; keeps the soil rich and the roots active."},
    ],
    "Mango": [
        {"name": "Urea / CAN (Nitrogen)", "purpose": "Apply after harvest to push a strong new leaf flush for next season's flowering."},
        {"name": "Muriate of Potash (MOP)", "purpose": "Apply 1–2 kg per grown tree; improves fruit set, size and sweetness."},
        {"name": "Farmyard Manure (Compost)", "purpose": "Apply 20–25 kg per tree yearly before flowering; strengthens roots and tree vigour."},
    ],
    "Banana": [
        {"name": "Urea (Nitrogen)", "purpose": "Banana is a heavy feeder — apply small doses monthly for fast, healthy leaf growth."},
        {"name": "Muriate of Potash (MOP)", "purpose": "Apply generously (banana needs the most potassium); improves bunch size and finger filling."},
        {"name": "Farmyard Manure (Compost)", "purpose": "Apply 10–15 kg per plant at planting; keeps soil moist and rich."},
    ],
    "Coffee": [
        {"name": "Balanced NPK (e.g. 17-17-17)", "purpose": "Apply after the monsoon in split doses; supports berry filling and new growth."},
        {"name": "Zinc + Boron (foliar)", "purpose": "Spray during flowering; improves berry set and reduces flower drop."},
        {"name": "Compost / Mulch", "purpose": "Mulch thickly under the bush; holds moisture and feeds the shallow roots."},
    ],
    "Cotton": [
        {"name": "Urea (Nitrogen)", "purpose": "Apply in splits at squaring and flowering; avoid excess or it delays bolls and attracts pests."},
        {"name": "DAP (Phosphorus)", "purpose": "Apply 40–50 kg per acre at sowing; builds strong early roots."},
        {"name": "MOP + Boron", "purpose": "Apply at boll development; improves boll size, fibre strength and reduces shedding."},
    ],
    "Rose": [
        {"name": "Balanced NPK (19-19-19)", "purpose": "Apply monthly in the growing season; supports steady flowering."},
        {"name": "Epsom Salt (Magnesium)", "purpose": "Spray 5 g per litre monthly; keeps leaves dark green and healthy."},
        {"name": "Vermicompost / FYM", "purpose": "Mix into the bed each season; feeds the roots gently and improves soil."},
    ],
    "Sugarcane": [
        {"name": "Urea (Nitrogen)", "purpose": "Apply in 2–3 splits up to grand-growth stage for strong, tall canes."},
        {"name": "Muriate of Potash (MOP)", "purpose": "Apply for stalk strength, juice quality and resistance to lodging."},
        {"name": "Press Mud / FYM", "purpose": "Apply before planting; improves soil health and moisture holding."},
    ],
}

# ── Per-crop farmer safety & expert tips ────────────────────────────────────
CROP_SAFETY = {
    "Rice": [
        "Walk the field weekly and check leaf tips and collars for spots — blast and blight start small.",
        "Split the nitrogen dose; excess urea at once invites blast, blight and sheath diseases.",
        "Keep steady water and good drainage, and remove weeds and old stubble that carry disease.",
    ],
    "Soybean": [
        "Scout for leaf spots and yellow-mosaic weekly, especially at the pod-forming stage.",
        "Control whiteflies early (they spread Yellow Mosaic Virus) with neem and yellow sticky traps.",
        "Rotate with a cereal (maize/wheat) and use certified, treated seed.",
    ],
    "Grape": [
        "Walk the vineyard weekly and check both leaf sides and the bunches for early spots.",
        "Thin the canopy so air moves freely and berries dry fast after rain or dew.",
        "Disinfect pruning tools between vines and remove mummified berries.",
    ],
    "Mango": [
        "Prune the canopy so sunlight and air reach inside — a dry canopy resists anthracnose and mildew.",
        "Collect and burn fallen leaves, flowers and fruit that carry the fungus to next season.",
        "Spray at flowering and fruit-set in the cool morning; control hoppers to stop sooty mould.",
    ],
    "Banana": [
        "Cut off and destroy old and Sigatoka-spotted leaves every week to slow the spread.",
        "Keep proper spacing and good drainage so leaves dry quickly.",
        "Remove weeds and de-sucker regularly so the mother plant gets full nourishment.",
    ],
    "Coffee": [
        "Maintain the right shade and prune for airflow — dense, damp bushes catch rust fast.",
        "Remove and destroy rust-infected leaves and spray protectants before the monsoon.",
        "Scout leaf undersides weekly for orange rust powder and for mite bronzing.",
    ],
    "Cotton": [
        "Scout for whitefly weekly (it spreads leaf curl virus) and use yellow sticky traps.",
        "Remove and destroy diseased plants and avoid excess nitrogen that attracts pests.",
        "Use certified, treated seed and rotate the field away from cotton when possible.",
    ],
    "Rose": [
        "Remove fallen and spotted leaves regularly and keep the bed clean.",
        "Water at the base in the morning, never over the leaves in the evening.",
        "Prune for good airflow and give plants enough spacing.",
    ],
    "Sugarcane": [
        "Use only disease-free setts from a healthy crop — most red-rot starts from bad seed cane.",
        "Rogue out and burn any clump showing red rot; never take ratoon from a diseased crop.",
        "Ensure good drainage and remove weeds and trash that harbour disease.",
    ],
}


# ─────────────────────────────────────────────────────────────
# Authored entries for the NEW (non-PlantVillage) classes
# ─────────────────────────────────────────────────────────────
NEW = {
    # ── RICE ─────────────────────────────────────────────
    "Bacterial Blight": D(
        "Rice", "Bacterial Leaf Blight",
        ["Water-soaked yellow streaks along the leaf edges that turn white/grey.",
         "Leaves dry from the tip and margins downward.",
         "In seedlings, whole leaves wilt and roll (kresek)."],
        "Xanthomonas oryzae bacteria, spread by rain, irrigation water and wind.",
        ["Use resistant varieties and balanced nitrogen (avoid excess urea).",
         "Drain the field periodically and remove infected stubble and weeds.",
         "Spray fresh cow-dung slurry extract as a mild bio-protectant."],
        ["Copper oxychloride 50% WP — 3 g per litre, spray at first symptoms.",
         "Streptocycline 0.5 g + Copper oxychloride 3 g per litre for severe spread."],
        ["Use certified, disease-free seed and treat it before sowing.",
         "Avoid heavy nitrogen and keep field drainage good.",
         "Remove weeds and infected stubble that carry the bacteria."],
        affected=["Leaves"]),
    "Bacterial Streak": D(
        "Rice", "Bacterial Leaf Streak",
        ["Thin, translucent streaks between the veins that turn yellow-brown.",
         "Tiny amber bacterial beads ooze on the streaks in humid weather.",
         "Severe streaking makes the whole leaf look brown and dry."],
        "Xanthomonas oryzae pv. oryzicola bacteria, spread by rain splash and wounds.",
        ["Use resistant varieties and balanced fertiliser.",
         "Avoid working in the field when leaves are wet.",
         "Drain excess water and remove infected debris."],
        ["Copper oxychloride 50% WP — 3 g per litre at early streaking.",
         "Streptocycline 0.5 g + Copper 3 g per litre if it spreads fast."],
        ["Use clean, certified seed and treat before sowing.",
         "Avoid excess nitrogen and standing water.",
         "Remove weed hosts around the bunds."],
        affected=["Leaves"]),
    "Bakanae": D(
        "Rice", "Bakanae (Foot Rot)",
        ["Seedlings grow abnormally tall, thin and pale yellow.",
         "Affected plants have long internodes and often die before flowering.",
         "Panicles are empty or partly filled; a pink fungal growth may show at the base."],
        "Seed-borne fungus Fusarium fujikuroi, carried on infected grain.",
        ["Treat seed with hot water (53–54°C for 10–12 minutes) before sowing.",
         "Coat seed with Trichoderma and use only healthy, certified seed.",
         "Remove and destroy abnormally tall seedlings early."],
        ["Carbendazim 50% WP — seed treatment at 2 g per kg of seed.",
         "Carbendazim 1 g per litre nursery drench if infection appears."],
        ["Always use disease-free, treated seed.",
         "Do not save seed from an infected crop.",
         "Rogue out tall, pale seedlings before transplanting."],
        affected=["Whole plant", "Seedlings", "Grains"]),
    "Brown Spot": D(
        "Rice", "Brown Spot",
        ["Small, oval to circular dark-brown spots on the leaves.",
         "A yellow halo often surrounds the brown lesions.",
         "Infected grains become discoloured, shrivelled or spotted."],
        "Fungus Bipolaris oryzae, worst in poor, nutrient-starved or drought-stressed soils.",
        ["Add well-decomposed compost and correct potassium and zinc deficiency.",
         "Treat seed with hot water or a Trichoderma coat before sowing.",
         "Spray Neem oil (5 ml/L) at the first appearance of spots."],
        ["Mancozeb 75% WP — 2.5 g per litre at early stage.",
         "Propiconazole 25% EC — 1 ml per litre for severe spread, repeat after 12–15 days."],
        ["Keep balanced nutrition — the disease thrives in weak, hungry crops.",
         "Ensure good drainage and avoid drought stress.",
         "Use certified, treated seed."],
        affected=["Leaves", "Grains"]),
    "False Smut": D(
        "Rice", "False Smut",
        ["Individual grains turn into velvety orange-green then black smut balls.",
         "Only a few grains per panicle are usually affected.",
         "Smut balls burst and release greenish-black spore powder."],
        "Fungus Ustilaginoidea virens, favoured by high nitrogen and humid weather at flowering.",
        ["Avoid late, heavy nitrogen application.",
         "Remove and destroy smutted panicles and infected stubble.",
         "Use resistant varieties where available."],
        ["Copper oxychloride 3 g per litre at booting stage.",
         "Propiconazole 25% EC — 1 ml per litre at booting and again at heading."],
        ["Do not over-apply nitrogen, especially late.",
         "Use clean seed and destroy infected residue.",
         "Give good field drainage."],
        affected=["Grains", "Panicle"]),
    "Grassy Stunt Virus": D(
        "Rice", "Grassy Stunt Virus",
        ["Severe stunting with many short, erect tillers (grassy look).",
         "Leaves are short, narrow, pale green to yellow with rusty spots.",
         "Few or no panicles form."],
        "A virus spread by the brown planthopper insect.",
        ["Control the brown planthopper with Neem oil (5 ml/L) and light traps.",
         "Grow resistant varieties and avoid dense planting.",
         "Rogue out and destroy infected plants early."],
        ["Manage the planthopper vector: Imidacloprid 0.3 ml per litre or Pymetrozine as advised.",
         "Spot-spray hopper hot-spots rather than the whole field."],
        ["Use resistant varieties and healthy seedlings.",
         "Avoid excess nitrogen that boosts planthopper build-up.",
         "Keep field bunds weed-free."],
        affected=["Whole plant", "Leaves"]),
    "Hispa": D(
        "Rice", "Rice Hispa",
        ["White parallel streaks where the beetle scrapes the green leaf surface.",
         "Grubs mine inside the leaf, causing pale blister-like patches.",
         "Heavily attacked fields look whitish and dry."],
        "The rice hispa beetle (Dicladispa armigera) and its leaf-mining grubs.",
        ["Sweep the crop with a hand net in early morning to collect adult beetles.",
         "Clip and destroy leaf tips carrying grubs; avoid excess nitrogen.",
         "Spray Neem oil (5 ml/L) on affected patches."],
        ["Chlorpyriphos 20% EC — 2 ml per litre on hot-spots.",
         "Quinalphos 25% EC — 2 ml per litre if the attack is heavy."],
        ["Avoid excess nitrogen and dense planting.",
         "Keep bunds clean of grassy weeds.",
         "Scout early and act on the first white streaks."],
        best="Early morning, when the beetles are slow and easy to knock down.",
        affected=["Leaves"]),
    "Leaf Blast": D(
        "Rice", "Leaf Blast",
        ["Spindle or diamond-shaped spots with grey centres and brown margins.",
         "Spots enlarge and join, drying whole leaves.",
         "Severe blast can kill young plants in patches."],
        "Fungus Magnaporthe oryzae, favoured by high humidity, dew and excess nitrogen.",
        ["Split the nitrogen dose into 3 applications instead of one heavy dose.",
         "Treat seed with Trichoderma or Pseudomonas before sowing.",
         "Spray Neem oil (5 ml/L) or a cow-dung + cow-urine extract at first lesions."],
        ["Tricyclazole 75% WP — 0.6 g per litre at first symptoms.",
         "Isoprothiolane 40% EC — 1.5 ml per litre, repeat after 12–15 days."],
        ["Use resistant varieties and treated seed.",
         "Avoid excess nitrogen and drain excess water.",
         "Do not let dew-wet, dense canopies stay damp."],
        affected=["Leaves"]),
    "Leaf_Blast": D(
        "Rice", "Leaf Blast",
        ["Spindle or diamond-shaped spots with grey centres and brown margins.",
         "Spots enlarge and merge, drying whole leaves.",
         "Young plants may die in patches under heavy infection."],
        "Fungus Magnaporthe oryzae, favoured by high humidity, dew and excess nitrogen.",
        ["Split the nitrogen dose into 3 applications.",
         "Treat seed with Trichoderma or Pseudomonas before sowing.",
         "Spray Neem oil (5 ml/L) at the first lesions."],
        ["Tricyclazole 75% WP — 0.6 g per litre at first symptoms.",
         "Isoprothiolane 40% EC — 1.5 ml per litre, repeat after 12–15 days."],
        ["Use resistant varieties and treated seed.",
         "Avoid excess nitrogen and keep drainage good.",
         "Reduce leaf wetness in dense canopies."],
        affected=["Leaves"]),
    "Neck Blast": D(
        "Rice", "Neck Blast",
        ["The node/neck just below the panicle turns black and rots.",
         "Panicles break over or stay erect but empty (whiteheads).",
         "Big yield loss because grains do not fill."],
        "The blast fungus Magnaporthe oryzae infecting the panicle neck at heading.",
        ["Use resistant varieties and balanced, split nitrogen.",
         "Treat seed with bio-agents and keep the crop unstressed.",
         "Remove infected stubble after harvest."],
        ["Tricyclazole 75% WP — 0.6 g per litre sprayed at booting and at heading.",
         "Azoxystrobin + Difenoconazole as a protectant spray at heading."],
        ["Spray protectant at booting BEFORE the neck is infected.",
         "Avoid late, heavy nitrogen.",
         "Grow blast-resistant varieties."],
        best="Spray at booting–heading in the cool morning, before infection sets in.",
        affected=["Panicle", "Neck / Node"]),
    "Leaf Scald": D(
        "Rice", "Leaf Scald",
        ["Zonate (banded) lesions spreading from the leaf tip and margins.",
         "Light-brown to straw-coloured bands with dark reddish edges.",
         "Leaf tips look scalded and dry."],
        "Fungus Microdochium oryzae, worse in high nitrogen and dense, humid canopies.",
        ["Balance nitrogen and avoid dense planting.",
         "Remove infected leaves and stubble.",
         "Spray Neem oil (5 ml/L) at first banding."],
        ["Copper oxychloride 3 g per litre at early stage.",
         "Propiconazole 25% EC — 1 ml per litre if it spreads."],
        ["Avoid excess nitrogen and crowding.",
         "Use clean seed.",
         "Improve airflow and drainage."],
        affected=["Leaves"]),
    "Leaf Smut": D(
        "Rice", "Leaf Smut",
        ["Small, black, slightly raised angular spots (smut sori) on the leaves.",
         "Spots are scattered on both leaf surfaces.",
         "Badly infected leaf tips may split and dry."],
        "Fungus Entyloma oryzae; usually a minor, late-season disease.",
        ["Balanced fertiliser keeps plants strong and less affected.",
         "Remove and destroy infected stubble after harvest.",
         "Use clean seed."],
        ["Usually not needed; if severe, Propiconazole 25% EC — 1 ml per litre.",
         "A single protectant Copper spray can check spread."],
        ["Avoid excess nitrogen.",
         "Keep field sanitation good.",
         "Grow tolerant varieties."],
        affected=["Leaves"]),
    "Narrow Brown Spot": D(
        "Rice", "Narrow Brown Spot",
        ["Short, narrow, dark-brown linear spots along the leaf veins.",
         "Similar streaks appear on leaf sheaths and grain hulls.",
         "Heavy infection dries the leaves late in the season."],
        "Fungus Cercospora janseana (Sphaerulina oryzina), worse with low potassium.",
        ["Correct potassium deficiency with MOP.",
         "Use resistant varieties and clean seed.",
         "Remove infected residue after harvest."],
        ["Propiconazole 25% EC — 1 ml per litre at early spotting.",
         "Mancozeb 75% WP — 2.5 g per litre as a protectant."],
        ["Keep potassium levels adequate.",
         "Avoid late nitrogen.",
         "Use tolerant varieties."],
        affected=["Leaves", "Sheath"]),
    "Sheath Blight": D(
        "Rice", "Sheath Blight",
        ["Oval, greenish-grey water-soaked lesions on the sheath near the water line.",
         "Lesions develop a light centre with a brown border (snake-skin banding).",
         "The disease climbs up the plant and can kill leaves and reduce filling."],
        "Soil fungus Rhizoctonia solani, favoured by dense planting and high nitrogen.",
        ["Avoid dense planting and excess nitrogen.",
         "Improve drainage and remove weed hosts on the bunds.",
         "Apply Trichoderma to the soil / as a spray."],
        ["Validamycin 3% L — 2 ml per litre at early lesions.",
         "Hexaconazole 5% EC — 2 ml per litre, repeat after 12–15 days."],
        ["Use wider spacing and balanced nitrogen.",
         "Keep good drainage.",
         "Remove infected stubble and sclerotia after harvest."],
        affected=["Sheath", "Leaves", "Stem"]),
    "Sheath Rot": D(
        "Rice", "Sheath Rot",
        ["Reddish-brown, irregular rot on the flag-leaf sheath that encloses the panicle.",
         "The panicle stays partly trapped and does not emerge fully.",
         "Grains are unfilled, discoloured or covered in a whitish powder."],
        "Fungus Sarocladium oryzae, worse in dense, humid crops and after insect damage.",
        ["Balance nitrogen and avoid dense planting.",
         "Control leaf-sheath insects that create entry wounds.",
         "Use clean seed and remove infected debris."],
        ["Carbendazim 50% WP — 1 g per litre at booting.",
         "Propiconazole 25% EC — 1 ml per litre at booting–heading."],
        ["Avoid crowding and excess nitrogen.",
         "Manage insect pests early.",
         "Use resistant varieties and clean seed."],
        best="Spray at booting–heading in the cool morning.",
        affected=["Sheath", "Panicle", "Grains"]),
    "Stem Rot": D(
        "Rice", "Stem Rot",
        ["Small black lesions on the outer sheath near the water line.",
         "The stem rots and blackens inside, weakening the plant.",
         "Plants lodge (fall over) and grains fill poorly."],
        "Fungus Sclerotium oryzae, which survives as sclerotia in soil and stubble.",
        ["Add potassium (MOP) for stronger stems.",
         "Destroy stubble and let sclerotia dry out; avoid stagnant water.",
         "Rotate and keep field sanitation good."],
        ["Hexaconazole 5% EC — 2 ml per litre at early stage.",
         "Propiconazole 25% EC — 1 ml per litre if it spreads."],
        ["Keep potassium adequate for strong stems.",
         "Remove and burn infected stubble.",
         "Avoid continuous stagnant flooding."],
        affected=["Stem", "Sheath"]),
    "Tungro": D(
        "Rice", "Tungro",
        ["Leaves turn yellow to orange, starting from the tip.",
         "Plants are stunted with reduced tillering.",
         "Panicles are small with many unfilled grains."],
        "A virus complex spread by the green leafhopper insect.",
        ["Control the green leafhopper with Neem oil (5 ml/L) and light traps.",
         "Grow resistant varieties and synchronise planting in the area.",
         "Rogue out and destroy infected plants early."],
        ["Manage the leafhopper vector: Imidacloprid 0.3 ml per litre on hot-spots.",
         "Spot-spray hopper patches rather than the whole field."],
        ["Use resistant varieties and healthy seedlings.",
         "Plant on time with neighbours to break the vector cycle.",
         "Remove infected plants and weed hosts."],
        affected=["Whole plant", "Leaves"]),
    "Ragged Stunt Virus": D(
        "Rice", "Ragged Stunt Virus",
        ["Twisted, ragged and notched leaf edges.",
         "Stunted plants with dark-green, crinkled leaves.",
         "Delayed heading and poorly filled, deformed panicles."],
        "A virus spread by the brown planthopper insect.",
        ["Control the brown planthopper with Neem oil (5 ml/L) and light traps.",
         "Grow resistant varieties and avoid dense planting.",
         "Rogue out infected plants."],
        ["Manage the planthopper vector: Imidacloprid 0.3 ml per litre or Pymetrozine as advised.",
         "Spot-treat hopper build-ups early."],
        ["Use resistant varieties and healthy seedlings.",
         "Avoid excess nitrogen that boosts hoppers.",
         "Keep bunds weed-free."],
        affected=["Whole plant", "Leaves", "Panicle"]),

    # ── MANGO ────────────────────────────────────────────
    "Anthracnose": D(
        "Mango", "Anthracnose",
        ["Dark, sunken black spots on leaves, flowers and young fruit.",
         "Blossom blight — flowers blacken and drop, reducing fruit set.",
         "Ripening fruit shows spreading black rotten patches."],
        "Fungus Colletotrichum gloeosporioides, spread by rain and humidity.",
        ["Prune for an open canopy and collect and burn fallen leaves, flowers and fruit.",
         "Spray a copper-based solution or Neem oil (5 ml/L) at flowering.",
         "Give ripe fruit a hot-water dip (52°C for 5 minutes) after harvest."],
        ["Carbendazim 50% WP — 1 g per litre at flowering and fruit-set.",
         "Mancozeb 75% WP — 2.5 g per litre as a protectant every 12–15 days."],
        ["Prune to open the canopy for sunlight and airflow.",
         "Remove and destroy fallen infected material.",
         "Start protectant sprays before the rains."],
        affected=["Leaves", "Flowers", "Fruits"]),
    "Bacterial Canker": D(
        "Mango", "Bacterial Canker",
        ["Water-soaked spots on leaves that become dark, raised cankers.",
         "Cracks and gum ooze from stems and fruit.",
         "Severe infection causes leaf fall and fruit drop."],
        "Bacterium Xanthomonas citri pv. mangiferaeindicae, spread by wind-driven rain and wounds.",
        ["Prune out and burn cankered twigs; avoid injuring the tree.",
         "Spray copper-based solution at leaf flush and fruit-set.",
         "Keep the tree vigorous with balanced nutrition."],
        ["Copper oxychloride 50% WP — 3 g per litre sprays.",
         "Streptocycline 0.5 g + Copper 3 g per litre for severe cases."],
        ["Avoid wounding the tree; disinfect pruning tools.",
         "Remove and burn cankered wood.",
         "Use windbreaks to cut rain-splash spread."],
        affected=["Leaves", "Stem", "Fruits"]),
    "Cutting Weevil": D(
        "Mango", "Cutting Weevil",
        ["Neat cuts and notches on leaf edges and tender shoots.",
         "Young shoots are severed and drop off.",
         "Grubs may bore into shoots, wilting the tips."],
        "The mango cutting weevil (Deporaus marginatus) feeding on tender growth.",
        ["Collect and destroy fallen cut shoots and adult weevils.",
         "Spray Neem oil (5 ml/L) on new flush.",
         "Encourage natural predators by avoiding broad-spectrum sprays."],
        ["Quinalphos 25% EC — 2 ml per litre on new flush.",
         "Lambda-cyhalothrin 5% EC — 1 ml per litre if attack is heavy."],
        ["Protect the tender new flush with timely sprays.",
         "Remove and destroy cut shoots.",
         "Keep the orchard clean."],
        affected=["Leaves", "Shoots"]),
    "Die Back": D(
        "Mango", "Die Back",
        ["Twigs die back from the tip downward, turning dark brown.",
         "A clear line separates dead and healthy wood; gum may ooze.",
         "Leaves on affected twigs droop, brown and fall."],
        "Fungus Lasiodiplodia theobromae, entering through wounds and stressed wood.",
        ["Prune 15 cm below the dead portion and seal cuts with Bordeaux paste.",
         "Keep the tree vigorous and avoid water/nutrient stress.",
         "Remove and burn dead wood."],
        ["Copper oxychloride 50% WP — 3 g per litre after pruning.",
         "Carbendazim 1 g per litre on fresh pruning cuts."],
        ["Prune well below the dead wood and protect the cuts.",
         "Avoid tree stress and injuries.",
         "Disinfect tools between trees."],
        affected=["Twigs", "Branches", "Leaves"]),
    "Gall Midge": D(
        "Mango", "Gall Midge",
        ["Small pimple-like galls (bumps) on leaves, buds and flowers.",
         "Leaves become distorted and may dry around the galls.",
         "Heavy attack on flower buds reduces fruit set."],
        "Tiny gall midge flies whose larvae develop inside the plant tissue.",
        ["Prune and destroy galled leaves and flower parts.",
         "Plough the soil under the tree to expose pupae.",
         "Spray Neem oil (5 ml/L) on new flush and flowering."],
        ["Dimethoate 30% EC — 1.5 ml per litre at bud burst / flowering.",
         "Lambda-cyhalothrin 5% EC — 1 ml per litre if severe."],
        ["Remove and destroy galled material early.",
         "Expose soil-borne pupae by light tillage.",
         "Protect flush and flowers with timely sprays."],
        affected=["Leaves", "Buds", "Flowers"]),
    "Powdery Mildew": D(
        "Mango", "Powdery Mildew",
        ["White powdery growth on flower panicles, young leaves and fruitlets.",
         "Flowers and tiny fruit dry up and drop heavily.",
         "Badly hit panicles turn brown and set no fruit."],
        "Fungus Oidium mangiferae, favoured by cool nights and dry days at flowering.",
        ["Dust or spray wettable sulphur (2 g/L) at early flowering.",
         "Spray a diluted milk solution (1:9) or Neem oil (5 ml/L) on sunny mornings.",
         "Prune for airflow so panicles dry quickly."],
        ["Wettable Sulphur 80% WP — 2 g per litre at panicle stage.",
         "Hexaconazole 5% EC — 2 ml per litre or Dinocap if it spreads."],
        ["Start protectant sprays as soon as panicles emerge.",
         "Avoid dense, shaded canopies.",
         "Grow tolerant varieties where possible."],
        affected=["Flowers", "Leaves", "Fruits"]),
    "Sooty Mould": D(
        "Mango", "Sooty Mould",
        ["A black, soot-like coating on the upper leaf surface.",
         "The black layer wipes off, revealing green leaf underneath.",
         "Heavy coating blocks sunlight and weakens the tree."],
        "Sooty fungi growing on the sugary honeydew left by hoppers, scales and mealybugs.",
        ["Control the sap-sucking insects (hoppers/scales) with Neem oil (5 ml/L).",
         "Spray a 1% starch/maida solution — it flakes off the mould as it dries.",
         "Wash leaves with a gentle water spray."],
        ["Manage the insects: Imidacloprid 0.3 ml per litre for hoppers.",
         "Add Neem oil to sprays to reduce honeydew build-up."],
        ["Control hoppers and scales early — no honeydew means no sooty mould.",
         "Prune for airflow and sunlight.",
         "Keep the orchard clean."],
        affected=["Leaves", "Twigs"]),
    "Healthy": healthy_entry("Mango", "The mango leaf is green and clean with no spots, mould or insect damage."),

    # ── BANANA ───────────────────────────────────────────
    "Banana_Cordana": D(
        "Banana", "Cordana Leaf Spot",
        ["Large oval pale-brown spots with a bright yellow halo.",
         "Spots often start at the leaf margin and spread inward.",
         "Spots merge and dry big areas of the leaf."],
        "Fungus Cordana musae, spread by rain splash in humid conditions.",
        ["Cut off and destroy heavily spotted old leaves.",
         "Keep proper spacing and drainage so leaves dry fast.",
         "Spray a copper-based solution or Neem oil (5 ml/L)."],
        ["Mancozeb 75% WP — 2.5 g per litre every 12–15 days.",
         "Copper oxychloride 50% WP — 3 g per litre as a protectant."],
        ["Remove old, infected leaves regularly.",
         "Avoid overcrowding and waterlogging.",
         "Maintain balanced nutrition."],
        affected=["Leaves"]),
    "Banana_Sigatoka": D(
        "Banana", "Sigatoka Leaf Spot",
        ["Yellow streaks that become brown-to-black spots with grey centres.",
         "Spots run parallel to the veins and merge, drying large leaf areas.",
         "Severe attack kills many leaves and reduces bunch size."],
        "Fungi Mycosphaerella (Sigatoka), spread by wind and rain in warm humid weather.",
        ["De-leaf and destroy spotted leaves weekly to slow spread.",
         "Improve spacing, drainage and weed control for airflow.",
         "Spray mineral/Neem oil to check early infection."],
        ["Propiconazole 25% EC — 1 ml per litre (often with mineral oil), repeat as needed.",
         "Mancozeb 75% WP — 2.5 g per litre as a protectant."],
        ["Remove infected leaves promptly and destroy them.",
         "Avoid dense plantings and waterlogging.",
         "Follow a regular protectant spray schedule in the rains."],
        affected=["Leaves"]),
    "Banana_Pestalotiopsis": D(
        "Banana", "Pestalotiopsis Leaf Blight",
        ["Brown to greyish leaf spots with a darker margin.",
         "Spots enlarge into blighted patches, often from the leaf tip/edge.",
         "Tiny black dots (fungal fruiting bodies) appear in old spots."],
        "Fungus Pestalotiopsis, usually entering through wounds and weakened tissue.",
        ["Remove and destroy blighted leaves and debris.",
         "Avoid leaf injury and keep plants unstressed.",
         "Spray copper or Neem oil (5 ml/L) as protection."],
        ["Mancozeb 75% WP — 2.5 g per litre every 12–15 days.",
         "Copper oxychloride 50% WP — 3 g per litre."],
        ["Keep the plantation clean and well-drained.",
         "Avoid mechanical injury to leaves.",
         "Maintain balanced nutrition for vigour."],
        affected=["Leaves"]),
    "Banana_Healthy": healthy_entry("Banana", "The banana leaf is broad, green and clean with no spots or blight."),

    # ── COFFEE ───────────────────────────────────────────
    "Coffee_Rust": D(
        "Coffee", "Coffee Leaf Rust",
        ["Yellow-orange powdery spots on the underside of the leaves.",
         "Matching pale yellow patches on the upper surface.",
         "Heavy rust causes early leaf drop and weak, bare branches."],
        "Fungus Hemileia vastatrix, spread by wind and rain in warm humid weather.",
        ["Maintain the right shade and prune for airflow.",
         "Remove and destroy rust-infected leaves.",
         "Spray 1% Bordeaux mixture before and during the monsoon."],
        ["Copper oxychloride 50% WP — 3 g per litre as a protectant.",
         "Hexaconazole 5% EC — 2 ml per litre or Triadimefon for active rust."],
        ["Grow rust-tolerant varieties.",
         "Manage shade and spacing for a dry canopy.",
         "Start protectant sprays before the rains."],
        affected=["Leaves"]),
    "Coffee_Miner": D(
        "Coffee", "Leaf Miner",
        ["Pale, winding or blotchy mines inside the leaf.",
         "Mined areas turn brown and brittle.",
         "Heavy mining causes leaf drop and weak plants."],
        "Larvae of the coffee leaf-miner moth feeding inside the leaf tissue.",
        ["Pinch and destroy mined leaves.",
         "Encourage natural parasitoids by avoiding harsh sprays.",
         "Spray Neem oil (5 ml/L) on new flush."],
        ["Spray a recommended insecticide (e.g. Quinalphos 2 ml/L) only on hot-spots.",
         "Add Neem-based sprays to protect natural enemies."],
        ["Keep bushes vigorous with good nutrition and shade.",
         "Remove mined leaves early.",
         "Protect natural predators — avoid unnecessary sprays."],
        affected=["Leaves"]),
    "Coffee_Phoma": D(
        "Coffee", "Phoma Leaf Spot & Dieback",
        ["Dark brown to black spots on leaf tips and margins.",
         "Young shoots blacken and die back in cool, wet, windy weather.",
         "Flowers and young berries may also blacken and drop."],
        "Fungus Phoma / Ascochyta, favoured by cold, wet and windy conditions.",
        ["Provide windbreaks and prune damaged shoots.",
         "Remove and destroy affected leaves and twigs.",
         "Spray a copper-based solution before cold wet spells."],
        ["Copper oxychloride 50% WP — 3 g per litre as a protectant.",
         "A systemic fungicide (e.g. Carbendazim 1 g/L) for active dieback."],
        ["Use windbreaks to reduce cold-wind injury.",
         "Keep plants unstressed and well-nourished.",
         "Prune and destroy affected wood."],
        affected=["Leaves", "Shoots", "Berries"]),
    "Coffee_Red_Spider_Mite": D(
        "Coffee", "Red Spider Mite",
        ["Fine yellow speckling then bronzing of the upper leaf surface.",
         "Tiny reddish mites and fine webbing on the underside.",
         "Severe attack dries and drops the leaves."],
        "Red spider mites (Oligonychus), worst in hot, dry, dusty weather.",
        ["Spray a strong jet of plain water to knock off mites and dust.",
         "Spray Neem oil (5 ml/L) or wettable sulphur.",
         "Keep plants watered — stressed bushes suffer most."],
        ["Wettable Sulphur 80% WP — 2 g per litre.",
         "A recommended miticide (e.g. Spiromesifen) if the attack is severe."],
        ["Avoid dust build-up on leaves (dust favours mites).",
         "Keep bushes well-watered and healthy.",
         "Protect predatory mites by avoiding broad sprays."],
        best="Evening or early morning, when it is cool — mites thrive in hot dry afternoons.",
        affected=["Leaves"]),
    "Coffee_Healthy": healthy_entry("Coffee", "The coffee leaf is dark green and glossy with no spots, rust or mite damage."),

    # ── COTTON ───────────────────────────────────────────
    "Cotton_Diseased_Leaf": D(
        "Cotton", "Diseased Leaf",
        ["Leaf spots, yellowing, curling or reddening that signal disease or pest attack.",
         "Angular water-soaked spots (bacterial blight) or upward leaf curl (leaf-curl virus).",
         "Reduced, weak growth in the affected part of the plant."],
        "A range of causes — bacterial blight, fungal leaf spots, or whitefly-borne leaf-curl virus.",
        ["Remove and destroy diseased leaves and control whitefly with Neem oil (5 ml/L).",
         "Use yellow sticky traps for whitefly (the leaf-curl virus carrier).",
         "Avoid excess nitrogen that softens plants."],
        ["For bacterial spots: Copper oxychloride 3 g per litre (+ Streptocycline 0.5 g).",
         "For fungal spots: Mancozeb 75% WP — 2.5 g per litre.",
         "For leaf curl: control whitefly with Imidacloprid 0.3 ml per litre."],
        ["Use certified, treated seed and resistant varieties.",
         "Scout and control whitefly early.",
         "Rogue out severely virus-infected plants."],
        affected=["Leaves"]),
    "Cotton_Diseased_Plant": D(
        "Cotton", "Diseased Plant",
        ["Overall stunting, yellowing, wilting or leaf curl across the plant.",
         "Poor boll development and shedding of squares/bolls.",
         "Signs of pest attack (whitefly, jassids) or root/wilt disease."],
        "Whole-plant stress from wilt, root disease, viral leaf-curl, or heavy sucking-pest attack.",
        ["Remove and destroy badly affected plants to protect the rest.",
         "Control sucking pests (whitefly/jassid) with Neem oil (5 ml/L) and traps.",
         "Improve drainage and avoid water stress."],
        ["Manage sucking pests: Imidacloprid 0.3 ml per litre where advised.",
         "For fungal wilt/root rot, drench with Carbendazim 1 g per litre + improve soil health."],
        ["Use resistant varieties and certified, treated seed.",
         "Rotate crops and improve soil drainage.",
         "Scout weekly and act on the first symptoms."],
        affected=["Whole plant", "Leaves", "Bolls"]),
    "Cotton_Healthy_Leaf": healthy_entry("Cotton", "The cotton leaf is green and firm with no spots, curling or pest damage."),
    "Cotton_Healthy_Plant": healthy_entry("Cotton", "The cotton plant is vigorous and green with healthy leaves and good boll set."),

    # ── ROSE ─────────────────────────────────────────────
    "Rose_Rust": D(
        "Rose", "Rust",
        ["Bright orange powdery pustules on the underside of the leaves.",
         "Yellow spots on the upper surface above the pustules.",
         "Heavy rust yellows and drops the leaves."],
        "Fungus Phragmidium, spread by wind and water in cool, moist weather.",
        ["Remove and destroy rust-infected leaves and fallen debris.",
         "Improve airflow and water at the base only.",
         "Spray wettable sulphur (2 g/L) or Neem oil (5 ml/L)."],
        ["Mancozeb 75% WP — 2.5 g per litre every 10–12 days.",
         "Hexaconazole 5% EC — 2 ml per litre for active rust."],
        ["Give plants good spacing and airflow.",
         "Avoid wetting the leaves in the evening.",
         "Remove fallen infected leaves regularly."],
        affected=["Leaves"]),
    "Rose_sawfly_Rose_slug": D(
        "Rose", "Sawfly (Rose Slug)",
        ["Leaves skeletonised — only a thin, papery window layer left.",
         "Slug-like green larvae feeding on the leaf underside.",
         "Heavy feeding gives a scorched, brown look to the bush."],
        "Larvae (rose slugs) of sawfly insects feeding on the leaf tissue.",
        ["Handpick and destroy the larvae in the morning.",
         "Spray a strong jet of water to dislodge them.",
         "Spray Neem oil (5 ml/L) or Spinosad on the underside."],
        ["Spinosad 45% SC — 0.3 ml per litre on the larvae.",
         "A recommended contact insecticide if the attack is heavy."],
        ["Scout leaf undersides weekly and act early.",
         "Encourage birds and natural predators.",
         "Keep the bed clean of debris."],
        affected=["Leaves"]),
    "Healthy_Leaf_Rose": healthy_entry("Rose", "The rose leaf is glossy green and clean with no rust, spots or chewing damage."),

    # ── SOYBEAN ──────────────────────────────────────────
    "Bacterial Pustule": D(
        "Soybean", "Bacterial Pustule",
        ["Small pale-green spots with a tiny raised pustule at the centre.",
         "Spots turn brown and often have a yellow halo.",
         "Spots merge, giving leaves a ragged, torn look."],
        "Bacterium Xanthomonas axonopodis pv. glycines, spread by rain splash and wounds.",
        ["Use resistant varieties and certified, treated seed.",
         "Avoid overhead irrigation and working among wet plants.",
         "Remove infected debris after harvest."],
        ["Copper oxychloride 50% WP — 3 g per litre at early symptoms.",
         "Streptocycline 0.5 g + Copper 3 g per litre for severe spread."],
        ["Grow resistant varieties.",
         "Use clean seed and rotate with cereals.",
         "Avoid leaf wetness and mechanical injury."],
        affected=["Leaves"]),
    "Frogeye Leaf Spot": D(
        "Soybean", "Frogeye Leaf Spot",
        ["Circular spots with grey centres and reddish-brown borders (frog-eye look).",
         "Spots may join and drop out, giving a shot-hole appearance.",
         "Severe spotting causes early leaf drop and pod/seed spots."],
        "Fungus Cercospora sojina, favoured by warm humid weather.",
        ["Grow resistant varieties and use clean, treated seed.",
         "Rotate with a non-host crop and destroy residue.",
         "Avoid dense, humid canopies."],
        ["Azoxystrobin 23% SC — 1 ml per litre at early spotting.",
         "Tebuconazole 25% EC — 1 ml per litre, repeat after 12–15 days."],
        ["Use resistant varieties and treated seed.",
         "Rotate crops and manage residue.",
         "Do not over-thicken the canopy."],
        affected=["Leaves", "Pods", "Seeds"]),
    "Sudden Death Syndrome": D(
        "Soybean", "Sudden Death Syndrome",
        ["Bright yellow blotches between the veins that turn brown (veins stay green).",
         "Leaflets drop but the stalk stays attached.",
         "Roots and lower stem are rotted with blue-grey mould inside."],
        "Soil fungus Fusarium virguliforme; worse in cool, wet, compacted soils.",
        ["Improve drainage and reduce soil compaction.",
         "Use resistant/tolerant varieties and high-quality seed.",
         "Rotate away from soybean and manage cyst nematode."],
        ["No effective rescue spray once established; use a good fungicide seed treatment at sowing.",
         "Focus on prevention — variety choice, drainage and seed treatment."],
        ["Choose tolerant varieties for problem fields.",
         "Avoid planting into cold, wet, compacted soil.",
         "Rotate and manage soybean cyst nematode."],
        affected=["Leaves", "Roots", "Stem"]),
    "Target Leaf Spot": D(
        "Soybean", "Target Leaf Spot",
        ["Circular brown spots with concentric rings, like a shooting target.",
         "Spots have a yellow halo and may join into large blotches.",
         "Severe infection drops leaves and spots the stems and pods."],
        "Fungus Corynespora cassiicola, favoured by warm, humid, dense canopies.",
        ["Improve airflow and avoid dense planting.",
         "Rotate with a non-host crop and destroy residue.",
         "Use clean, treated seed."],
        ["Mancozeb 75% WP — 2.5 g per litre as a protectant.",
         "Azoxystrobin 23% SC — 1 ml per litre for active spread."],
        ["Avoid overly dense canopies.",
         "Rotate crops and manage residue.",
         "Use resistant varieties where available."],
        affected=["Leaves", "Stem", "Pods"]),
    "Yellow Mosaic": D(
        "Soybean", "Yellow Mosaic Virus",
        ["Bright yellow and green mosaic patches scattered on the leaves.",
         "Leaves become puckered and reduced in size.",
         "Plants are stunted with few, poorly filled pods."],
        "A whitefly-borne geminivirus (Mungbean/Soybean Yellow Mosaic Virus).",
        ["Control whiteflies (the carrier) with Neem oil (5 ml/L) and yellow sticky traps.",
         "Rogue out and destroy infected plants early.",
         "Grow resistant/tolerant varieties."],
        ["Manage whitefly: Imidacloprid 0.3 ml per litre or Thiamethoxam as advised.",
         "Spot-spray whitefly hot-spots and field borders."],
        ["Use resistant varieties and certified seed.",
         "Control whitefly from early growth.",
         "Remove weed hosts and infected plants."],
        affected=["Leaves", "Whole plant"]),
    "Soybean_Healthy": healthy_entry("Soybean", "The soybean leaf is green and clean with no spots, mosaic or mite damage."),

    # ── SUGARCANE ────────────────────────────────────────
    "Red Rot": D(
        "Sugarcane", "Red Rot",
        ["Drying and yellowing of leaves from the top, then whole cane.",
         "Split cane shows red internal tissue with white cross-bands.",
         "A sour, alcohol-like smell from the affected cane."],
        "Fungus Colletotrichum falcatum, carried in setts and soil; the most serious cane disease.",
        ["Use only disease-free setts from a healthy crop.",
         "Treat setts with hot water or a Trichoderma/Carbendazim dip before planting.",
         "Rogue out and burn affected clumps; do not ratoon a diseased crop."],
        ["Carbendazim 50% WP — sett dip at 1 g per litre before planting.",
         "Soil/soil-line drench with Carbendazim around early infected clumps."],
        ["Plant resistant varieties and healthy setts.",
         "Avoid ratooning an infected crop.",
         "Ensure good drainage and field sanitation."],
        affected=["Stem / Cane", "Leaves"]),
    "Rust": D(
        "Sugarcane", "Rust",
        ["Small elongated orange-brown pustules on the leaves.",
         "Pustules are mostly on the underside and run along the veins.",
         "Heavy rust dries the leaves and weakens the cane."],
        "Fungus Puccinia, spread by wind in warm, humid weather.",
        ["Grow rust-tolerant varieties and avoid dense planting.",
         "Remove badly infected old leaves.",
         "Maintain balanced nutrition and drainage."],
        ["Mancozeb 75% WP — 2.5 g per litre as a protectant.",
         "Propiconazole 25% EC — 1 ml per litre for active rust."],
        ["Use tolerant varieties.",
         "Give proper spacing for airflow.",
         "Keep the crop well-nourished and drained."],
        affected=["Leaves"]),

    # ── GRAPE (standalone dataset, prefix-less) ──────────
    "Black Rot": D(
        "Grape", "Black Rot",
        ["Small tan leaf spots with a dark border and tiny black dots inside.",
         "Berries develop brown rot, then shrivel into hard black mummies.",
         "Infected shoots and tendrils show dark sunken lesions."],
        "Fungus Guignardia bidwellii, surviving in mummified berries and canes.",
        ["Remove and destroy mummified berries and infected canes.",
         "Improve airflow by thinning shoots and leaves.",
         "Spray 1% Bordeaux mixture from bud-break, repeating every 10 days."],
        ["Mancozeb 75% WP — 2.5 g per litre as a protectant.",
         "Myclobutanil or Difenoconazole for active infection."],
        ["Sanitise — remove all mummies and infected wood.",
         "Open the canopy for airflow and sunlight.",
         "Start protectant sprays early in the season."],
        affected=["Leaves", "Fruits", "Shoots"]),
    "ESCA": D(
        "Grape", "Esca (Black Measles)",
        ["Leaves show 'tiger-stripe' bands of yellow/red between green veins.",
         "Berries get small dark spots (measles) and may crack.",
         "Vines can suddenly wilt (apoplexy) in hot weather; wood rots inside."],
        "A complex of wood-rotting fungi that enter through pruning wounds.",
        ["Prune out and burn affected arms/cordons; disinfect tools between vines.",
         "Protect large pruning wounds with Trichoderma or Bordeaux paste.",
         "Never prune in wet weather."],
        ["No spray cures Esca; protect pruning wounds with a Trichoderma-based product.",
         "Remove and destroy severely affected vines."],
        ["Prune in dry weather and protect the cuts.",
         "Disinfect pruning tools between vines.",
         "Keep vines vigorous and unstressed."],
        affected=["Leaves", "Fruits", "Trunk / Wood"]),
    "Leaf Blight": D(
        "Grape", "Leaf Blight",
        ["Irregular brown to dark blotches on the leaves.",
         "Blotches enlarge and dry, often starting from the leaf margin.",
         "Severe blight causes early leaf drop and weak vines."],
        "Fungus Pseudocercospora / Isariopsis, favoured by warm, humid, wet weather.",
        ["Remove infected leaves and thin the canopy for airflow.",
         "Spray 1% Bordeaux mixture or Neem oil (5 ml/L) every 10–12 days.",
         "Avoid overhead watering."],
        ["Mancozeb 75% WP — 2.5 g per litre as a protectant.",
         "Copper oxychloride 50% WP — 3 g per litre during the monsoon."],
        ["Open the canopy for airflow.",
         "Remove infected leaves and debris.",
         "Follow a protectant spray schedule in the rains."],
        affected=["Leaves"]),
}


def attach_crop_extras(entry):
    """Add crop-specific fertilizers + safety tips; append chemical-handling
    lines when the entry recommends a chemical spray."""
    crop = entry.get("crop", "")
    entry["fertilizers"] = [dict(f) for f in CROP_FERTILIZERS.get(crop, entry.get("fertilizers", []))]
    safety = list(CROP_SAFETY.get(crop, entry.get("safety_tips", [])))
    if entry.get("chemical_spray"):
        safety = safety + CHEMICAL_SAFETY
    entry["safety_tips"] = safety
    entry.setdefault("farmer_tips", safety[:3])
    entry.setdefault("treatment", [])
    return entry


def build():
    with open(CLASSES, 'r', encoding='utf-8') as f:
        class_names = json.load(f)
    with open(BACKUP, 'r', encoding='utf-8') as f:
        preserved = json.load(f)

    out = {}
    missing = []
    for name in class_names:
        if name in NEW:
            out[name] = attach_crop_extras(dict(NEW[name]))
        elif name in preserved:
            out[name] = preserved[name]          # keep rich PlantVillage entry
        else:
            missing.append(name)
            # Safe generic fallback so nothing is left without an entry.
            crop, _, disease = name.partition('___')
            disease = disease or name
            out[name] = attach_crop_extras(D(
                crop.replace('_', ' ') or name, disease.replace('_', ' '),
                symptoms=["Refer to a local expert for exact symptoms."],
                cause="", organic=HEALTHY_CARE, chemical=[],
                prevent=["Use certified seed and keep the field clean."],
                healthy=('healthy' in name.lower())))

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[build_disease_info] Wrote {len(out)} entries -> {OUT}")
    print(f"   from NEW: {sum(1 for n in class_names if n in NEW)} | "
          f"preserved: {sum(1 for n in class_names if n in preserved and n not in NEW)} | "
          f"fallback: {len(missing)}")
    if missing:
        print("   FALLBACK (no authored/preserved entry):")
        for m in missing:
            print("     -", m)


if __name__ == '__main__':
    build()
