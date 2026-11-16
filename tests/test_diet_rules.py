import json
from pathlib import Path

import pytest
from src import diet_rules

SNAPSHOT = Path(__file__).resolve().parent.parent / 'data' / 'products.json'
PRODUCTS = json.loads(SNAPSHOT.read_text())['products']


def evidence(text, allergens=(), traces=(), complete=True):
    return dict(ingredients_text=text, allergens=list(allergens), traces=list(traces), complete=complete)


# 1. Every real Open Food Facts product gets the diet we read from its label (v1 got 16/17)
@pytest.mark.parametrize('product', PRODUCTS, ids=[p['name'] for p in PRODUCTS])
def test_classify_real_products(product):
    diet, reason = diet_rules.classify(product['evidence'], product['name'])
    assert diet == product['expected_diet'], reason


# 2. v2: the product name is evidence
def test_bacon_with_cure_only_ingredients_is_non_vegetarian():
    diet, reason = diet_rules.classify(evidence('Water, salt, sugar, sodium nitrite'), 'Original Bacon')
    assert diet == 'non-vegetarian'
    assert reason == 'Name says bacon (not in the ingredients list)'


def test_without_a_name_the_cure_only_bacon_is_still_vegan():
    # v1 behaviour is kept when no name is passed, so old callers don't change
    assert diet_rules.classify(evidence('Water, salt, sugar, sodium nitrite'))[0] == 'vegan'


@pytest.mark.parametrize('name', ['Veggie Bacon Strips', 'Plant-Based Chicken Nuggets', 'Meatless Sausage',
                                  'Vegan Fish Sticks', 'Imitation Crab'])
def test_plant_based_names_do_not_count_as_meat(name):
    assert diet_rules.classify(evidence('soy protein, wheat gluten, oil, salt'), name)[0] == 'vegan'


def test_name_does_not_rescue_an_animal_ingredient():
    # "Veggie" in the name can't make egg whites vegan: ingredients always win
    assert diet_rules.classify(evidence('egg whites, spinach'), 'Veggie Egg Bites')[0] == 'vegetarian'


def test_name_meat_beats_dairy_ingredients():
    assert diet_rules.classify(evidence('cheese, salt'), 'Bacon Cheese Dip')[0] == 'non-vegetarian'


def test_name_plural_and_case():
    assert diet_rules.classify(evidence('water, salt'), 'SMOKED SAUSAGES')[0] == 'non-vegetarian'


def test_name_word_inside_another_word_is_ignored():
    # 'ham' inside 'Graham', 'eggs' inside 'Eggplant' style traps
    assert diet_rules.classify(evidence('wheat flour, sugar'), 'Graham Crackers')[0] == 'vegan'


# 3. Which users can eat which product
@pytest.mark.parametrize('user_diet, product_text, allowed', [
    ('vegan', 'water, organic soybeans', True),
    ('vegan', "pasteurized cow's milk, salt", False),
    ('vegetarian', 'eggs', True),
    ('vegetarian', 'swordfish', False),
    ('non-vegetarian', 'swordfish', True),
])
def test_fits_diet(user_diet, product_text, allowed):
    assert diet_rules.fits_diet(user_diet, evidence(product_text))[0] is allowed


def test_fits_diet_uses_the_name():
    allowed, reason = diet_rules.fits_diet('vegetarian', evidence('water, salt, sugar'), 'Original Bacon')
    assert not allowed
    assert 'bacon' in reason


def test_incomplete_evidence_is_withheld():
    allowed, reason = diet_rules.fits_diet('vegan', evidence('water, sugar', complete=False))
    assert not allowed
    assert reason.startswith('Withheld')


def test_unknown_diet_cannot_be_assessed():
    allowed, reason = diet_rules.fits_diet('keto', evidence('water'))
    assert not allowed
    assert reason == 'Cannot assess diet: keto'


# 4. Traps from v1: words that look animal but are not, and missing tags
@pytest.mark.parametrize('text', ['peanut butter, salt', 'oat milk, sugar', 'cocoa butter, sugar', 'eggplant, olive oil'])
def test_plant_phrases_are_vegan(text):
    assert diet_rules.classify(evidence(text))[0] == 'vegan'


def test_trace_only_stays_vegan_with_note():
    diet, reason = diet_rules.classify(evidence('durum wheat semolina', traces=['eggs']))
    assert diet == 'vegan'
    assert 'may contain traces of eggs' in reason
