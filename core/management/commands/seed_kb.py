from django.core.management.base import BaseCommand
from core.models import Symptom, Rule

SYMPTOMS = [
    # code, label, crop
    ("yellow_leaves", "Yellowing leaves", "general"),
    ("wilting", "Wilting despite adequate water", "general"),
    ("stunted_growth", "Stunted / slow growth", "general"),
    ("holes_in_leaves", "Ragged holes chewed in leaves", "general"),
    ("white_powder", "White powdery coating on leaves", "general"),
    ("black_spots", "Black or brown spots on leaves", "general"),
    ("sticky_residue", "Sticky honeydew residue on leaves", "general"),
    ("curled_leaves", "Leaves curling or distorted", "general"),
    ("holes_in_stem", "Tunnels/holes bored into stem", "maize"),
    ("sawdust_frass", "Sawdust-like frass near stem base", "maize"),
    ("silk_damage", "Damaged or chewed maize silk", "maize"),
    ("fruit_rot", "Soft rot on fruit", "tomato"),
    ("leaf_mold", "Fuzzy grey-green mold under leaves", "tomato"),
    ("blossom_end_rot", "Dark sunken patch at fruit bottom", "tomato"),
    ("pod_holes", "Small holes in pods", "beans"),
    ("root_nodule_absence", "Poor nodulation / pale plants", "beans"),
    ("head_splitting", "Cabbage head splitting open", "cabbage"),
    ("clubbed_roots", "Swollen, club-shaped roots", "cabbage"),
    ("tuber_scab", "Rough scabby patches on tubers", "potato"),
    ("blackened_stems", "Blackened, collapsing stems", "potato"),
]

RULES = [
    # crop, conclusion, symptoms(list of codes), base_cf, advice
    ("maize", "Fall Armyworm infestation",
     ["holes_in_leaves", "sawdust_frass", "holes_in_stem"], 0.85,
     "Scout early morning; apply recommended biopesticide (e.g. Bt-based) or "
     "targeted insecticide on whorls; introduce natural predators where possible; "
     "rotate maize with a non-host crop next season."),
    ("maize", "Maize streak virus",
     ["yellow_leaves", "stunted_growth", "curled_leaves"], 0.6,
     "Remove and destroy infected plants; control leafhopper vectors with "
     "appropriate insecticide; plant certified virus-resistant seed next season."),
    ("maize", "Nitrogen deficiency",
     ["yellow_leaves", "stunted_growth"], 0.55,
     "Apply top-dressing nitrogen fertiliser (e.g. Urea/CAN) at recommended rate; "
     "confirm with a soil test before repeat application."),

    ("tomato", "Late blight",
     ["black_spots", "fruit_rot", "wilting"], 0.8,
     "Remove and destroy infected plants immediately; apply a copper-based or "
     "systemic fungicide; avoid overhead irrigation; improve field drainage/airflow."),
    ("tomato", "Powdery mildew",
     ["white_powder", "curled_leaves"], 0.75,
     "Apply sulfur-based or systemic fungicide; increase plant spacing for airflow; "
     "avoid excess nitrogen which encourages soft, susceptible growth."),
    ("tomato", "Blossom end rot (calcium/water stress)",
     ["blossom_end_rot", "wilting"], 0.7,
     "Maintain even soil moisture with mulching/consistent irrigation; apply "
     "calcium foliar spray; avoid heavy fertiliser swings."),
    ("tomato", "Grey mold (Botrytis)",
     ["leaf_mold", "fruit_rot"], 0.65,
     "Improve ventilation, remove infected plant debris, apply appropriate fungicide, "
     "avoid working in wet foliage."),

    ("beans", "Bean weevil / pod borer",
     ["pod_holes", "holes_in_leaves"], 0.75,
     "Apply recommended insecticide at flowering/podding stage; practise field "
     "sanitation and destroy crop residue after harvest."),
    ("beans", "Poor rhizobium nodulation",
     ["root_nodule_absence", "stunted_growth", "yellow_leaves"], 0.6,
     "Inoculate seed with rhizobium at planting; apply modest phosphorus fertiliser; "
     "avoid excess nitrogen which suppresses nodulation."),

    ("cabbage", "Clubroot disease",
     ["clubbed_roots", "wilting", "stunted_growth"], 0.8,
     "Improve soil drainage and raise soil pH with lime; practise long crop rotation "
     "(4+ years) away from brassicas; remove and destroy infected plants."),
    ("cabbage", "Calcium/boron deficiency (head splitting)",
     ["head_splitting"], 0.55,
     "Ensure consistent watering to avoid growth spurts; apply calcium/boron foliar "
     "feed; harvest promptly once heads mature."),
    ("cabbage", "Aphid infestation",
     ["sticky_residue", "curled_leaves", "stunted_growth"], 0.7,
     "Spray insecticidal soap or recommended insecticide; encourage natural "
     "predators (ladybirds); remove heavily infested leaves."),

    ("potato", "Common scab",
     ["tuber_scab"], 0.65,
     "Lower soil pH slightly, maintain even soil moisture at tuber initiation, "
     "avoid fresh manure before planting, rotate with non-host crops."),
    ("potato", "Blackleg disease",
     ["blackened_stems", "wilting"], 0.75,
     "Remove and destroy affected plants; use certified disease-free seed potatoes; "
     "avoid waterlogged soil and improve drainage."),

    # Generic / cross-crop heuristics (lower confidence, broad symptom match)
    ("general", "General aphid / sap-sucking pest pressure",
     ["sticky_residue", "curled_leaves", "yellow_leaves"], 0.55,
     "Inspect leaf undersides for pests; apply insecticidal soap or targeted "
     "insecticide; monitor weekly."),
    ("general", "General fungal leaf disease",
     ["black_spots", "white_powder", "wilting"], 0.5,
     "Remove affected leaves, improve airflow/spacing, apply a broad-spectrum "
     "fungicide, avoid overhead watering late in the day."),
]


class Command(BaseCommand):
    help = "Seed the rule-based knowledge base with symptoms and expert rules."

    def handle(self, *args, **options):
        created_s = 0
        for code, label, crop in SYMPTOMS:
            _, created = Symptom.objects.get_or_create(
                code=code, defaults={"label": label, "crop": crop}
            )
            created_s += int(created)

        created_r = 0
        for crop, conclusion, symptoms, cf, advice in RULES:
            _, created = Rule.objects.get_or_create(
                crop=crop, conclusion=conclusion,
                defaults={"symptoms": symptoms, "base_cf": cf, "advice": advice},
            )
            created_r += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created_s} new symptoms and {created_r} new rules "
            f"(totals: {Symptom.objects.count()} symptoms, {Rule.objects.count()} rules)."
        ))
