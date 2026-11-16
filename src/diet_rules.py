"""Diet rules v2 for Pantry Path: is a grocery product vegan, vegetarian, or non-vegetarian?

`evidence` has the same shape Pantry Path's planner uses (from Open Food Facts):
    {'allergens': [...], 'traces': [...], 'complete': bool, 'ingredients_text': str}

Allergen tags are often missing (e.g. tuna with no 'fish' tag), so we check both
the tags and keywords in the ingredients text. Unknown is never guessed as safe.

v2 (this lab): the product name is evidence too. Some labels list only the cure
("Water, salt, sugar, sodium nitrite") for a product called "Original Bacon";
v1 called that vegan. A meat word in the name now makes it non-vegetarian,
unless the name also says it is plant-based ("Veggie Bacon", "Meatless Chicken").
"""
import re

DIETS = ('vegan', 'vegetarian', 'non-vegetarian')

# Allergen tags that reveal an animal source
MEAT_TAGS = {'fish', 'crustaceans', 'molluscs', 'gelatin', 'beef', 'pork', 'chicken'}
ANIMAL_PRODUCT_TAGS = {'milk', 'eggs', 'honey'}

# Ingredient words (singular; plurals are matched too)
MEAT_WORDS = ['meat', 'beef', 'pork', 'chicken', 'turkey', 'lamb', 'bacon', 'ham', 'sausage', 'lard', 'tallow',
              'gelatin', 'gelatine', 'fish', 'tuna', 'salmon', 'swordfish', 'anchovy', 'anchovies', 'sardine',
              'shrimp', 'prawn', 'crab', 'lobster', 'shellfish', 'oyster', 'animal rennet', 'carmine']
ANIMAL_PRODUCT_WORDS = ['milk', 'cream', 'butter', 'cheese', 'whey', 'casein', 'lactose', 'yogurt', 'ghee',
                        'egg', 'honey']

# Plant phrases that contain an animal word ("peanut butter", "oat milk") and must not count
PLANT_PHRASES = ['peanut butter', 'nut butter', 'almond butter', 'cocoa butter', 'shea butter',
                 'oat milk', 'oatmilk', 'soy milk', 'almond milk', 'coconut milk', 'rice milk', 'coconut cream']

# Name words that mean "this is a plant-based version", so a meat word in the name doesn't count
PLANT_NAME_MARKERS = ['vegan', 'vegetarian', 'veggie', 'plant-based', 'plant based', 'meatless', 'meat-free',
                      'meat free', 'imitation', 'faux', 'mock']


def find_words(text, words):
    """Return the words from `words` that appear in `text` as whole words (plural 's' allowed)."""
    text = text.lower()
    for phrase in PLANT_PHRASES:
        text = text.replace(phrase, ' ')
    return [w for w in words if re.search(r'\b' + re.escape(w) + r's?\b', text)]


def unique(names):
    """Drop repeats, treating singular and plural as the same ('eggs' tag + 'egg' word -> 'eggs')."""
    seen, out = set(), []
    for name in names:
        if name.rstrip('s') not in seen:
            seen.add(name.rstrip('s'))
            out.append(name)
    return out


def meat_in_name(name):
    """Return the meat words in a product name, or [] if the name says it is plant-based."""
    lowered = (name or '').lower()
    if any(marker in lowered for marker in PLANT_NAME_MARKERS):
        return []
    return find_words(lowered, MEAT_WORDS)


def classify(evidence, name=None):
    """Classify a product. Returns (diet, reason), where diet is one of DIETS or 'unknown'.

    `name` is optional; when given, a meat word in it counts as evidence (see module docstring).
    """
    if not evidence.get('complete') or not evidence.get('ingredients_text', '').strip():
        return 'unknown', 'Incomplete ingredient evidence'
    tags = set(evidence.get('allergens', []))
    text = evidence['ingredients_text']

    meat = sorted(tags & MEAT_TAGS) + find_words(text, MEAT_WORDS)
    if meat:
        return 'non-vegetarian', 'Contains ' + ', '.join(unique(meat))
    named = meat_in_name(name)
    if named:
        return 'non-vegetarian', 'Name says ' + ', '.join(unique(named)) + ' (not in the ingredients list)'
    animal = sorted(tags & ANIMAL_PRODUCT_TAGS) + find_words(text, ANIMAL_PRODUCT_WORDS)
    if animal:
        return 'vegetarian', 'Contains ' + ', '.join(unique(animal))

    # Traces ("may contain") are cross-contact, not ingredients: still vegan, but say so
    trace_animal = sorted(set(evidence.get('traces', [])) & (MEAT_TAGS | ANIMAL_PRODUCT_TAGS))
    if trace_animal:
        return 'vegan', 'No animal ingredients; may contain traces of ' + ', '.join(trace_animal)
    return 'vegan', 'No animal ingredients found'


def fits_diet(diet, evidence, name=None):
    """Can a user on `diet` eat this product? Returns (allowed, reason)."""
    if diet not in DIETS:
        return False, f'Cannot assess diet: {diet}'
    if diet == 'non-vegetarian':
        return True, 'No diet restriction'
    product_diet, reason = classify(evidence, name)
    if product_diet == 'unknown':
        return False, 'Withheld: ' + reason
    allowed = product_diet == 'vegan' or (diet == 'vegetarian' and product_diet == 'vegetarian')
    return allowed, reason
