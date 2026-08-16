import json

trusted_treatments = {
    "Apple___Apple_scab": [
        {"name": "Captan 50% WP (Wettable Powder)", "purpose": "Contact fungicide for protective control", "application": "Foliar spray at petal fall", "dosage": "2.0g per liter", "interval": "Every 7-10 days", "safety": "Wear protective gear"},
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Prevents spore germination", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Observe pre-harvest interval"},
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic fungicide for curative/preventive action", "application": "Foliar spray during early infection", "dosage": "1.0g per liter", "interval": "Every 14 days", "safety": "Low toxicity to beneficials"}
    ],
    "Apple___Black_rot": [
        {"name": "Captan 50% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Foliar spray", "dosage": "2.0g per liter", "interval": "Every 10-14 days", "safety": "Wear protective gear"},
        {"name": "Thiophanate-methyl 70% WP (Wettable Powder)", "purpose": "Systemic treatment for cankers", "application": "Apply to pruning wounds", "dosage": "1.5g per liter", "interval": "During dormant season", "safety": "Store away from food"}
    ],
    "Apple___Cedar_apple_rust": [
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic fungicide effective against rust", "application": "Foliar spray at pink bud stage", "dosage": "1.0g per liter", "interval": "Every 7-10 days", "safety": "Wear basic protective equipment"},
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective fungicide", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-14 days", "safety": "Do not apply near water sources"}
    ],
    "Cherry_(including_sour)___Powdery_mildew": [
        {"name": "Wettable Sulfur 80% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Foliar spray on affected areas", "dosage": "3.0g per liter", "interval": "Every 7-10 days", "safety": "Do not apply above 30°C to avoid leaf burn"},
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic fungicide", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 14 days", "safety": "Low toxicity"},
        {"name": "Potassium Bicarbonate (Organic Fungicide)", "purpose": "Organic fungicide", "application": "Foliar spray", "dosage": "5.0g per liter", "interval": "Every 7 days", "safety": "Safe for humans and environment"}
    ],
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": [
        {"name": "Azoxystrobin 23% SC (Suspension Concentrate)", "purpose": "Systemic strobilurin", "application": "Foliar spray at tasseling", "dosage": "1.0ml per liter", "interval": "Single application, repeat if needed", "safety": "Avoid spray drift"},
        {"name": "Propiconazole 25% EC (Emulsifiable Concentrate)", "purpose": "Systemic triazole", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14-21 days", "safety": "Wear protective clothing"}
    ],
    "Corn_(maize)___Common_rust_": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective fungicide", "application": "Foliar spray at first pustule appearance", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Do not apply near harvest"},
        {"name": "Tebuconazole 25.9% EC (Emulsifiable Concentrate)", "purpose": "Broad-spectrum systemic control", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14-21 days", "safety": "Low toxicity to non-targets"}
    ],
    "Corn_(maize)___Northern_Leaf_Blight": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective fungicide", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Standard precautions"},
        {"name": "Azoxystrobin + Propiconazole (Combined Systemic Fungicide)", "purpose": "Combined systemic control", "application": "Foliar spray at V12-VT stage", "dosage": "1.0ml per liter", "interval": "Single application", "safety": "Observe pre-harvest interval"}
    ],
    "Grape___Black_rot": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective pre-bloom application", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Do not apply after veraison"},
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic curative/protective", "application": "Foliar spray bloom and post-bloom", "dosage": "1.0g per liter", "interval": "Every 10-14 days", "safety": "Low mammalian toxicity"}
    ],
    "Grape___Esca_(Black_Measles)": [
        {"name": "Fosetyl-Al 80% WP (Wettable Powder)", "purpose": "Systemic fungicide for trunk diseases", "application": "Foliar spray during growing season", "dosage": "2.5g per liter", "interval": "Every 14-21 days", "safety": "Low toxicity"},
        {"name": "Trichoderma harzianum (Bio-Fungicide)", "purpose": "Biological wound protectant", "application": "Paste or spray on pruning cuts", "dosage": "As per label", "interval": "Immediately after pruning", "safety": "Organic approved"}
    ],
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Broad-spectrum protection", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Standard protective equipment"},
        {"name": "Copper Oxychloride 50% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Preventive foliar spray", "dosage": "3.0g per liter", "interval": "Every 14 days", "safety": "Avoid soil buildup"}
    ],
    "Orange___Haunglongbing_(Citrus_greening)": [
        {"name": "Imidacloprid 17.8% SL (Soluble Liquid)", "purpose": "Systemic vector control (Psyllid)", "application": "Soil drench or foliar", "dosage": "5.0ml per tree (soil) or 0.5ml/L (foliar)", "interval": "Every 30-45 days", "safety": "Highly toxic to bees, apply carefully"},
        {"name": "Chelated Micronutrients (Zinc, Manganese, Iron)", "purpose": "Nutritional therapy", "application": "Foliar spray", "dosage": "2.0g per liter", "interval": "Monthly", "safety": "Very safe, helps tree survive"}
    ],
    "Peach___Bacterial_spot": [
        {"name": "Copper Hydroxide 77% WP (Wettable Powder)", "purpose": "Bactericidal early season protection", "application": "Dormant and early foliar spray", "dosage": "2.0g per liter", "interval": "Every 7-10 days", "safety": "May cause phytotoxicity in warm weather"},
        {"name": "Oxytetracycline 17% WP (Wettable Powder)", "purpose": "Antibiotic for bacterial control", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 7 days", "safety": "Use where permitted"},
        {"name": "Copper + Mancozeb Mix (Combined Fungicide)", "purpose": "Reduces phytotoxicity", "application": "Foliar spray", "dosage": "1.5g Cu + 2.0g Mancozeb per liter", "interval": "Every 10-14 days", "safety": "Safer for leaves"}
    ],
    "Pepper,_bell___Bacterial_spot": [
        {"name": "Copper Oxychloride 50% WP (Wettable Powder)", "purpose": "Contact bactericide", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Wear gloves and mask"},
        {"name": "Streptomycin Sulfate (Bactericidal Antibiotic)", "purpose": "Antibiotic for suppression", "application": "Foliar spray", "dosage": "0.5g per liter", "interval": "Every 7-10 days", "safety": "Use where permitted"},
        {"name": "Copper Hydroxide + Mancozeb (Combined Fungicide/Bactericide)", "purpose": "Combined protection", "application": "Foliar spray", "dosage": "2.0g Cu + 2.5g Mancozeb per liter", "interval": "Every 10-14 days", "safety": "Observe pre-harvest interval"}
    ],
    "Potato___Early_blight": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Broad-spectrum protection", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Standard protective equipment"},
        {"name": "Chlorothalonil 75% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Preventive foliar spray", "dosage": "2.0g per liter", "interval": "Every 7-14 days", "safety": "Irritant to skin"},
        {"name": "Azoxystrobin 23% SC (Suspension Concentrate)", "purpose": "Systemic strobilurin", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14 days", "safety": "Low toxicity"}
    ],
    "Potato___Late_blight": [
        {"name": "Metalaxyl 8% + Mancozeb 64% WP (Wettable Powder)", "purpose": "Systemic + contact control", "application": "Foliar spray when conditions are predicted", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Alternate to prevent resistance"},
        {"name": "Cymoxanil 8% + Mancozeb 64% WP (Wettable Powder)", "purpose": "Curative and protective action", "application": "Foliar spray", "dosage": "3.0g per liter", "interval": "Every 7-10 days", "safety": "Observe pre-harvest interval"},
        {"name": "Copper Oxychloride 50% WP (Wettable Powder)", "purpose": "Contact fungicide (organic option)", "application": "Preventive foliar spray", "dosage": "3.0g per liter", "interval": "Every 5-7 days", "safety": "Approved for organic"}
    ],
    "Squash___Powdery_mildew": [
        {"name": "Sulfur 80% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Foliar spray", "dosage": "3.0g per liter", "interval": "Every 7-10 days", "safety": "Do not apply over 30°C"},
        {"name": "Neem Oil (Azadirachtin Organic Insecticide)", "purpose": "Natural fungicide", "application": "Foliar spray", "dosage": "5.0ml per liter", "interval": "Every 7 days", "safety": "Organic-approved"},
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic fungicide", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 14 days", "safety": "Low toxicity"}
    ],
    "Strawberry___Leaf_scorch": [
        {"name": "Captan 50% WP (Wettable Powder)", "purpose": "Broad-spectrum contact fungicide", "application": "Foliar spray", "dosage": "2.0g per liter", "interval": "Every 7-10 days", "safety": "Observe pre-harvest interval"},
        {"name": "Myclobutanil 10% WP (Wettable Powder)", "purpose": "Systemic control", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 14 days", "safety": "Safe for strawberries"},
        {"name": "Copper Oxychloride 50% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Foliar spray during renovation", "dosage": "2.5g per liter", "interval": "Every 14 days", "safety": "Reduce rate in hot weather"}
    ],
    "Tomato___Bacterial_spot": [
        {"name": "Copper Hydroxide 77% WP (Wettable Powder)", "purpose": "Primary bactericidal control", "application": "Foliar spray", "dosage": "2.0g per liter", "interval": "Every 5-7 days", "safety": "May cause phytotoxicity in heat"},
        {"name": "Copper + Mancozeb Tank Mix (Combined Fungicide)", "purpose": "Enhanced control with reduced phytotoxicity", "application": "Foliar spray", "dosage": "1.5g Cu + 2.0g Mancozeb per liter", "interval": "Every 7-10 days", "safety": "Standard protective equipment"},
        {"name": "Streptomycin Sulfate (Bactericidal Antibiotic)", "purpose": "Antibiotic for severe infection", "application": "Foliar spray", "dosage": "0.5g per liter", "interval": "Every 7-10 days", "safety": "Restricted in many regions"}
    ],
    "Tomato___Early_blight": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Broad-spectrum protective", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "5-day pre-harvest interval"},
        {"name": "Chlorothalonil 75% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Preventive foliar spray", "dosage": "2.0g per liter", "interval": "Every 7-14 days", "safety": "Irritant, wear protective clothing"},
        {"name": "Azoxystrobin 23% SC (Suspension Concentrate)", "purpose": "Systemic strobilurin", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14 days", "safety": "Low mammalian toxicity"}
    ],
    "Tomato___Late_blight": [
        {"name": "Metalaxyl + Mancozeb (Ridomil Gold - Systemic + Contact Fungicide)", "purpose": "Systemic + contact control", "application": "Foliar spray at first sign", "dosage": "2.5g per liter", "interval": "Every 10-14 days", "safety": "Alternate to prevent resistance"},
        {"name": "Cymoxanil + Mancozeb (Systemic + Contact Fungicide)", "purpose": "Curative and protective", "application": "Foliar spray", "dosage": "3.0g per liter", "interval": "Every 7-10 days", "safety": "Observe pre-harvest interval"},
        {"name": "Dimethomorph 50% WP (Wettable Powder)", "purpose": "Systemic oomycete specific", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 10-14 days", "safety": "Wear standard gear"}
    ],
    "Tomato___Leaf_Mold": [
        {"name": "Chlorothalonil 75% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Spray targeting leaf undersides", "dosage": "2.0g per liter", "interval": "Every 7-10 days", "safety": "Ensure greenhouse ventilation"},
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Broad-spectrum protection", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Standard protective equipment"},
        {"name": "Bacillus subtilis (Bio-Fungicide)", "purpose": "Biological fungicide", "application": "Preventive spray", "dosage": "As per label", "interval": "Every 7 days", "safety": "Organic-approved"}
    ],
    "Tomato___Septoria_leaf_spot": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective contact fungicide", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Pre-harvest interval 5 days"},
        {"name": "Chlorothalonil 75% WP (Wettable Powder)", "purpose": "Broad-spectrum contact", "application": "Preventive foliar spray", "dosage": "2.0g per liter", "interval": "Every 7-14 days", "safety": "Irritant"}
    ],
    "Tomato___Spider_mites Two-spotted_spider_mite": [
        {"name": "Abamectin 1.9% EC (Emulsifiable Concentrate)", "purpose": "Miticide/insecticide", "application": "Spray leaf undersides", "dosage": "0.5ml per liter", "interval": "Every 7 days", "safety": "Toxic to bees, do not apply during bloom"},
        {"name": "Spiromesifen 22.9% SC (Suspension Concentrate)", "purpose": "Specific miticide", "application": "Foliar spray", "dosage": "0.8ml per liter", "interval": "Every 14 days", "safety": "Low toxicity to beneficials"},
        {"name": "Neem Oil (Azadirachtin Organic Insecticide)", "purpose": "Natural miticide", "application": "Spray all surfaces", "dosage": "5.0ml per liter", "interval": "Every 5-7 days", "safety": "Organic-approved"}
    ],
    "Tomato___Target_Spot": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Protective contact fungicide", "application": "Foliar spray", "dosage": "2.5g per liter", "interval": "Every 7-10 days", "safety": "Standard protective equipment"},
        {"name": "Difenoconazole 25% EC (Emulsifiable Concentrate)", "purpose": "Systemic triazole for curative control", "application": "Foliar spray", "dosage": "0.5ml per liter", "interval": "Every 14 days", "safety": "Observe pre-harvest interval"},
        {"name": "Azoxystrobin 23% SC (Suspension Concentrate)", "purpose": "Systemic strobilurin", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14 days", "safety": "Low toxicity"}
    ],
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": [
        {"name": "Imidacloprid 17.8% SL (Soluble Liquid)", "purpose": "Systemic insecticide for Whitefly vector", "application": "Soil drench or foliar spray", "dosage": "0.5ml per liter", "interval": "Every 14 days", "safety": "Toxic to bees"},
        {"name": "Thiamethoxam 25% WG (Water Dispersible Granules)", "purpose": "Neonicotinoid for whitefly", "application": "Soil application at transplanting", "dosage": "0.5g per plant", "interval": "Single application", "safety": "Toxic to pollinators"},
        {"name": "Neem Oil (Azadirachtin Organic Insecticide)", "purpose": "Natural whitefly repellent", "application": "Foliar spray", "dosage": "5.0ml per liter", "interval": "Every 5-7 days", "safety": "Organic-approved"}
    ],
    "Tomato___Tomato_mosaic_virus": [
        {"name": "No Chemical Cure (Prevention Only)", "purpose": "Viral diseases cannot be cured", "application": "Focus on prevention/vector control", "dosage": "N/A", "interval": "N/A", "safety": "Remove infected plants immediately"},
        {"name": "Milk Spray (Organic Antiviral Solution)", "purpose": "Inactivates virus particles", "application": "Foliar spray", "dosage": "100ml per liter", "interval": "Every 7 days", "safety": "Completely safe"}
    ],
    "Rice_BrownSpot": [
        {"name": "Mancozeb 75% WP (Wettable Powder)", "purpose": "Contact fungicide", "application": "Foliar spray", "dosage": "2.0g per liter", "interval": "Every 10-15 days", "safety": "Wear protective gear"},
        {"name": "Propiconazole 25% EC (Emulsifiable Concentrate)", "purpose": "Systemic fungicide", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 15 days", "safety": "Avoid spray drift"},
        {"name": "Edifenphos 50% EC (Emulsifiable Concentrate)", "purpose": "Organophosphate fungicide", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 10-14 days", "safety": "Use standard PPE"},
        {"name": "Carbendazim 50% WP (Wettable Powder)", "purpose": "Systemic benzimidazole", "application": "Foliar spray", "dosage": "1.0g per liter", "interval": "Every 15 days", "safety": "Avoid continuous use to prevent resistance"}
    ],
    "Rice_Hispa": [
        {"name": "Chlorpyrifos 20% EC (Emulsifiable Concentrate)", "purpose": "Broad-spectrum insecticide", "application": "Foliar spray", "dosage": "2.5ml per liter", "interval": "When pest exceeds economic threshold", "safety": "Highly toxic, use full PPE"},
        {"name": "Quinalphos 25% EC (Emulsifiable Concentrate)", "purpose": "Contact and stomach insecticide", "application": "Foliar spray", "dosage": "2.0ml per liter", "interval": "As needed based on scouting", "safety": "Toxic to fish and bees"},
        {"name": "Lambda-cyhalothrin 5% EC (Emulsifiable Concentrate)", "purpose": "Pyrethroid insecticide", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "As needed", "safety": "Fast knockdown, wear mask"},
        {"name": "Neem Oil (Azadirachtin Organic Insecticide)", "purpose": "Organic repellent and antifeedant", "application": "Foliar spray", "dosage": "5.0ml per liter", "interval": "Every 7-10 days", "safety": "Safe for environment"}
    ],
    "Rice_LeafBlast": [
        {"name": "Tricyclazole 75% WP (Wettable Powder)", "purpose": "Specific systemic fungicide for blast", "application": "Foliar spray", "dosage": "0.6g per liter", "interval": "Every 10-14 days", "safety": "Highly effective, wear mask"},
        {"name": "Isoprothiolane 40% EC (Emulsifiable Concentrate)", "purpose": "Systemic fungicide", "application": "Foliar spray", "dosage": "1.5ml per liter", "interval": "Every 10-15 days", "safety": "Standard protective gear"},
        {"name": "Kasugamycin 3% SL (Soluble Liquid)", "purpose": "Antibiotic fungicide", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 10 days", "safety": "Follow label for safety"},
        {"name": "Azoxystrobin 25% SC (Suspension Concentrate)", "purpose": "Broad-spectrum strobilurin", "application": "Foliar spray", "dosage": "1.0ml per liter", "interval": "Every 14 days", "safety": "Toxic to aquatic life"}
    ]
}

def process():
    file_path = "c:/Users/monda/Desktop/Crop Deseases Detection/disease_info.json"
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for key, treatments in trusted_treatments.items():
        if key in data:
            data[key]["treatment"] = treatments

    # Make sure healthy classes have empty treatments
    for key in data.keys():
        if "healthy" in key.lower():
            data[key]["treatment"] = []

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    process()
