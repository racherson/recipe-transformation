import collections
import functools
import json
import nltk
# import pymongo
import urllib.request
from bs4 import BeautifulSoup
# from pprint import pprint


# TODOs

# TODO: comment code since there is no more presentation
# TODO: include ingredient style
# TODO: change unit when changing amount across 1 (use inflect)
# TODO: check units when merging ingredients
# TODO: lemmatize and conjugate when substituting methods in steps so tense is taken into consideration
# TODO: adjust method times when substituting ingredients
# TODO: use unique ingredients when altering steps (for loop where if full name not in use just name)
# TODO: include added ingredient names when substituting ingredients in steps
# TODO: add vegetarian substitutions for every type of meat


# global variables

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
STOPWORDS = nltk.corpus.stopwords.words('english')
PUNCTUATION = [',', '.', '!', '?', '(', ')']
STOPWORDS.extend(PUNCTUATION)
METHODS = ['add', 'use', 'blend', 'cut', 'strain', 'roast', 'slice', 'flip', 'baste', 'simmer', 'grate', 'drain', 'saute', 'broil', 'boil', 'poach', 'bake', 'grill', 'fry', 'bake', 'heat', 'mix', 'chop', 'grate', 'stir', 'shake', 'mince', 'crush', 'squeeze', 'dice', 'rub', 'cook']
TOOLS = ['pan', 'grater', 'whisk', 'pot', 'spatula', 'tong', 'oven', 'knife']
UNITS = ['tablespoon', 'teaspoon', 'cup', 'clove', 'pound']


# categorized foods (found at https://github.com/olivergoodman/food-recipes/blob/master/transforms.py)

INGREDIENT_CATEGORIES = {
    'healthy_fats': ['olive oil', 'sunflower oil', 'soybean oil', 'corn oil',  'sesame oil',  'peanut oil'],
    'unhealthy_fats': ['butter', 'lard', 'shortening', 'canola oil', 'margarine',  'coconut oil',  'tallow',  'cream',
                       'milk fat',  'palm oil',  'palm kemel oil',  'chicken fat',  'hydrogenated oils'],
    'healthy_protein': ['peas',  'beans', 'eggs', 'crab', 'fish', 'chicken', 'tofu', 'liver', 'turkey'],
    'unhealthy_protein': ['ground beef', 'beef', 'pork', 'lamb'],
    'meat': ['scallop', 'sausage', 'bacon', 'beef', 'pork', 'lamb', 'crab', 'fish', 'chicken', 'turkey', 'liver',
             'duck', 'tuna', 'lobster', 'salmon', 'shrimp', 'crayfish', 'crawfish', 'ribs', 'pheasant', 'escargot',
             'snail', 'bass', 'sturgeon', 'trout', 'flounder', 'carp', 'quail', 'goose'],
    'healthy_dairy': ['fat free milk', 'low fat milk', 'yogurt',  'low fat cheese'],
    'unhealthy_dairy': ['reduced-fat milk', 'cream cheese', 'whole milk', 'butter', 'cheese', 'whipped cream',
                        'sour cream'],
    'healthy_salts': ['low sodium soy sauce', 'sea salt', 'kosher salt'],
    'unhealthy_salts': ['soy sauce', 'table salt', 'salt'],
    'healthy_grains': ['oat cereal', 'wild rice', 'oatmeal', 'whole rye', 'buckwheat', 'rolled oats', 'quinoa',
                       'bulgur', 'millet', 'brown rice', 'whole wheat pasta'],
    'unhealthy_grains': ['macaroni', 'noodles', 'spaghetti', 'white rice', 'white bread', 'regular white pasta'],
    'healthy_sugars': ['real fruit jam', 'fruit juice concentrates', 'monk fruit extract', 'cane sugar', 'molasses',
                       'brown rice syrup' 'stevia', 'honey', 'maple syrup', 'agave syrup', 'coconut sugar',
                       'date sugar', 'sugar alcohols', 'brown sugar'],
    'unhealthy_sugars': ['aspartame', 'acesulfame K', 'sucralose', 'white sugar', 'corn syrup', 'chocolate syrup'],
    'spice': ['ajwain', 'allspice', 'almond meal', 'anise seed', 'annatto seed', 'arrowroot powder', 'cacao', 'cumin',
              'bell pepper', 'beetroot powder', 'chia seeds', 'cloves', 'chiles', 'cinnamon', 'cloves', 'coriander',
              'dill seed', 'garlic', 'ginger', 'mustard', 'onion', 'paprika', 'cayenne', 'pepper', 'red pepper',
              'black pepper', 'shallots', 'star anise', 'turmeric', 'vanilla extract'],
    'herb': ['basil', 'bay leaves', 'celery flakes', 'chervil', 'cilantro', 'curry', 'dill weed', 'dried chives',
             'epatoze', 'file powder', 'kaffire lime', 'lavender', 'lemongrass', 'mint', 'oregano', 'parsley',
             'rosemary', 'sage', 'tarragon', 'thyme']

}

SYNONYMS = {
    'stock': 'broth',
}


# recipe class definition

class Recipe:
    def __init__(self, soup):
        self.soup = soup
        # get recipe name
        name = self.soup.find('h1', id='recipe-main-content')
        self.name = name.string
        # get recipe ingredients
        ingredients = self.soup.find_all('span', class_='recipe-ingred_txt added')
        self.ingredients = [add_ingredient(ingredient.contents[0]) for ingredient in ingredients]
        # get recipe steps
        self.steps = self.get_steps()
        # get recipe tools
        self.tools, methods_counter = self.get_tools_methods()
        # get primary method (most mentioned) and any other methods
        self.primary_method = methods_counter.most_common(1)[0][0]
        del methods_counter[self.primary_method]
        self.other_methods = list(methods_counter)
        if self.primary_method == 'bake' or 'bake' in self.other_methods:
            self.bake = True
        else:
            self.bake = False
        # initialize ingredient and method switches dictionaries
        self.ingredient_switches = {}
        self.method_switches = {}
        # print recipe
        self.print_recipe()

    def get_steps(self):
        global SYNONYMS
        # get steps from soup
        steps_elements = self.soup.find('ol', class_='list-numbers recipe-directions__list')('li')
        steps = []
        for count, step_element in enumerate(steps_elements):
            step_text = str(count+1) + '. ' + step_element.find('span').string.strip()
            for synonym in SYNONYMS:
                step_text = step_text.replace(synonym, SYNONYMS[synonym])
            steps.append(Step(step_text, self.ingredients))
        return steps

    def get_tools_methods(self):
        global STOPWORDS
        global METHODS
        global TOOLS
        tools = set()  # unique set
        methods_counter = collections.Counter()  # frequency mapping
        for step in self.steps:
            tokens = nltk.word_tokenize(step.text)
            tokens = [token.lower() for token in tokens if token not in STOPWORDS]
            bigrams = nltk.bigrams(tokens)
            step_methods = set()
            # check unigrams for tools and methods
            for token in tokens:
                if token in TOOLS:
                    tools.add(token)
                if token in METHODS:
                    methods_counter.update([token])
                    step_methods.add(token)
            # check bigrams for tools and methods
            for token in bigrams:
                if token in TOOLS:
                    tools.add(token)
                if token in METHODS:
                    methods_counter.update([token])
                    step_methods.add(token)
            step.methods = list(step_methods)
        return list(tools), methods_counter

    def alter_steps(self):

        word_ends = [' ', '.', ',']
        for step in self.steps:
            for switch in self.ingredient_switches:
                for word_end in word_ends:
                    step.text = step.text.replace(switch + word_end, self.ingredient_switches[switch] + word_end)
            for switch in self.method_switches:
                for word_end in word_ends:
                    step.text = step.text.replace(switch + word_end, self.method_switches[switch] + word_end)

        # global PUNCTUATION
        # for step in self.steps:
        #     tokens = nltk.word_tokenize(step.text)
        #     altered_step_text = ''
        #     for token in tokens:
        #         if token == '(':
        #             altered_step_text += token
        #         elif token in PUNCTUATION:
        #             altered_step_text = altered_step_text[:-1] + token + ' '
        #         elif token.lower() in self.ingredient_switches:
        #             altered_step_text += self.ingredient_switches[token.lower()] + ' '
        #         elif token.lower in self.method_switches:
        #             altered_step_text += self.method_switches[token.lower()] + ' '
        #         else:
        #             altered_step_text += token + ' '
        #     step.text = altered_step_text[:-1]

    def make_healthy(self):
        print('\nMaking healthy...')
        if self.bake:
            global healthy_baking_substitutions_names
            global healthy_baking_substitutions_adjectives
            global healthy_baking_substitutions_categories
            global healthy_baking_substitutions_exceptions
            global healthy_baking_substitutions_methods
            for step in self.steps:
                make_substitutions_with(step.ingredients,
                                        self.ingredient_switches,
                                        healthy_baking_substitutions_names,
                                        healthy_baking_substitutions_adjectives,
                                        healthy_baking_substitutions_categories,
                                        healthy_baking_substitutions_exceptions,
                                        False)
                for method in step.methods:
                    if method in healthy_baking_substitutions_methods:
                        self.method_switches[method] = healthy_baking_substitutions_methods[method]
                step.methods = [self.method_switches[x] if x in self.method_switches else x for x in step.methods]
        else:
            global healthy_substitutions_names
            global healthy_substitutions_adjectives
            global healthy_substitutions_categories
            global healthy_substitutions_exceptions
            global healthy_substitutions_methods
            for step in self.steps:
                make_substitutions_with(step.ingredients,
                                        self.ingredient_switches,
                                        healthy_substitutions_names,
                                        healthy_substitutions_adjectives,
                                        healthy_substitutions_categories,
                                        healthy_substitutions_exceptions,
                                        False)
                for method in step.methods:
                    if method in healthy_substitutions_methods:
                        self.method_switches[method] = healthy_substitutions_methods[method]
                step.methods = [self.method_switches[x] if x in self.method_switches else x for x in step.methods]
        self.alter_steps()
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def make_unhealthy(self):
        print('\nMaking unhealthy...')
        if self.bake:
            global unhealthy_baking_substitutions_names
            global unhealthy_baking_substitutions_adjectives
            global unhealthy_baking_substitutions_categories
            global unhealthy_baking_substitutions_exceptions
            global unhealthy_baking_substitutions_methods
            for step in self.steps:
                make_substitutions_with(step.ingredients,
                                        self.ingredient_switches,
                                        unhealthy_baking_substitutions_names,
                                        unhealthy_baking_substitutions_adjectives,
                                        unhealthy_baking_substitutions_categories,
                                        unhealthy_baking_substitutions_exceptions,
                                        False)
                for method in step.methods:
                    if method in unhealthy_baking_substitutions_methods:
                        self.method_switches[method] = unhealthy_baking_substitutions_methods[method]
                step.methods = [self.method_switches[x] if x in self.method_switches else x for x in step.methods]
        else:
            global unhealthy_substitutions_names
            global unhealthy_substitutions_adjectives
            global unhealthy_substitutions_categories
            global unhealthy_substitutions_exceptions
            global unhealthy_substitutions_methods
            for step in self.steps:
                make_substitutions_with(step.ingredients,
                                        self.ingredient_switches,
                                        unhealthy_substitutions_names,
                                        unhealthy_substitutions_adjectives,
                                        unhealthy_substitutions_categories,
                                        unhealthy_substitutions_exceptions,
                                        False)
                for method in step.methods:
                    if method in unhealthy_substitutions_methods:
                        self.method_switches[method] = unhealthy_substitutions_methods[method]
                step.methods = [self.method_switches[x] if x in self.method_switches else x for x in step.methods]
        self.alter_steps()
        next_count = int(self.steps[-1].text[0]) + 1
        if not self.bake:
            salt = Ingredient('salt', None, 'seasoning', None, None)
            self.ingredients.append(salt)
            step_text = str(next_count) + '. Sprinkle a lot of extra salt over the whole meal.'
            new_step = Step(step_text, [salt])
            new_step.methods = ['sprinkle']
            self.steps.append(new_step)
        else:
            frosting = Ingredient('frosting', 'chocolate', 'topping', 2, 'cups')
            self.ingredients.append(frosting)
            step_text = str(next_count) + '. Spread frosting over everything.'
            new_step = Step(step_text, [frosting])
            new_step.methods = ['spread']
            self.steps.append(new_step)
        print('\nAltered Ingredients:')
        for ingredient in self.ingredients:
            print(ingredient)
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def make_vegetarian(self):
        global vegetarian_substitutions_names
        global vegetarian_substitutions_adjectives
        global vegetarian_substitutions_categories
        global vegetarian_substitutions_exceptions
        print('\nMaking vegetarian...')
        for step in self.steps:
            make_substitutions_with(step.ingredients,
                                    self.ingredient_switches,
                                    vegetarian_substitutions_names,
                                    vegetarian_substitutions_adjectives,
                                    vegetarian_substitutions_categories,
                                    vegetarian_substitutions_exceptions,
                                    True)
        self.alter_steps()
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def make_non_vegetarian(self):
        global non_vegetarian_substitutions_names
        global non_vegetarian_substitutions_adjectives
        global non_vegetarian_substitutions_categories
        global non_vegetarian_substitutions_exceptions
        print('\nMaking non-vegetarian...')
        for step in self.steps:
            make_substitutions_with(step.ingredients,
                                    self.ingredient_switches,
                                    non_vegetarian_substitutions_names,
                                    non_vegetarian_substitutions_adjectives,
                                    non_vegetarian_substitutions_categories,
                                    non_vegetarian_substitutions_exceptions,
                                    False)
        self.alter_steps()
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def make_thai(self):
        global thai_substitutions_names
        global thai_substitutions_adjectives
        global thai_substitutions_categories
        global thai_substitutions_exceptions
        print('\nMaking Thai...')
        for step in self.steps:
            make_substitutions_with(step.ingredients,
                                    self.ingredient_switches,
                                    thai_substitutions_names,
                                    thai_substitutions_adjectives,
                                    thai_substitutions_categories,
                                    thai_substitutions_exceptions,
                                    False)
        self.alter_steps()
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def make_mediterranean(self):
        global mediterranean_substitutions_names
        global mediterranean_substitutions_adjectives
        global mediterranean_substitutions_categories
        global mediterranean_substitutions_exceptions
        print('\nMaking Mediterranean...')
        for step in self.steps:
            make_substitutions_with(step.ingredients,
                                    self.ingredient_switches,
                                    mediterranean_substitutions_names,
                                    mediterranean_substitutions_adjectives,
                                    mediterranean_substitutions_categories,
                                    mediterranean_substitutions_exceptions,
                                    False)
        self.alter_steps()
        print('\nAltered Steps:')
        for step in self.steps:
            print(step)

    def print_recipe(self):
        print('\nName:', self.name)
        print('\nIngredients:')
        for ingredient in self.ingredients:
            print(ingredient)
        print('\nTools:', self.tools)
        print('\nPrimary Method:', self.primary_method)
        print('\nOther Methods:', self.other_methods)
        print('\nBaking?:', self.bake)
        print('\nSteps:')
        for step in self.steps:
            print(step)

    def jsonify(self):
        recipe = {'ingredients': self.ingredients,
                  'tools': self.tools,
                  'primary_method': self.primary_method,
                  'other_methods': self.other_methods,
                  'steps': self.steps}
        serializable = json.dumps(recipe)
        # pprint(serializable)
        return serializable


# step class definition

class Step:
    def __init__(self, step_text, ingredients):
        self.text = step_text
        self.ingredients = []
        self.methods = None
        ingredients_dict = {}
        for ingredient in ingredients:
            if ingredient.name in ingredients_dict:
                ingredients_dict[ingredient.name].append(ingredient)
            else:
                ingredients_dict[ingredient.name] = [ingredient]
        unique_ingredients_dict = {}
        for ingredient in ingredients_dict:
            if len(ingredients_dict[ingredient]) == 1:
                unique_ingredients_dict[ingredient] = ingredients_dict[ingredient][0]
            else:
                for ingredient_ref in ingredients_dict[ingredient]:
                    if ingredient_ref.adjective:
                        full_name = ingredient_ref.adjective + ' ' + ingredient
                        unique_ingredients_dict[full_name] = ingredient_ref
                    else:
                        unique_ingredients_dict[ingredient] = ingredient_ref
        for ingredient in unique_ingredients_dict:
            if ingredient in step_text.lower():
                self.ingredients.append(unique_ingredients_dict[ingredient])

    def __str__(self):
        output = self.text + '\nStep Ingredients:  '
        for ingredient in self.ingredients:
            output += str(ingredient) + ', '
        output = output[:-2] + '\nStep Methods:  '
        for method in self.methods:
            output += method + ', '
        return output[:-2]


# ingredient class definition

class Ingredient:
    def __init__(self, name, adjective, category, amount, unit):
        self.name = name
        self.adjective = adjective
        self.category = category
        self.amount = amount
        self.unit = unit

    def __str__(self):
        output = ''
        if self.amount:
            output += str(self.amount) + ' '
        if self.unit:
            output += self.unit + ' '
        if self.adjective:
            output += self.adjective + ' '
        return output + self.name


# ingredient instantiation functions

def ingredient_base(ingredient):
    ingredient.name = ingredient.adjective
    ingredient.adjective = None
    return ingredient_categorize(ingredient)


def ingredient_categorize(ingredient):
    # category = categorize(ingredient)
    # amount, unit = convert_measure(ingredient)
    # return Ingredient(ingredient.name, ingredient.adjective, category, amount, unit)
    return Ingredient(ingredient.name, ingredient.adjective, ingredient.category, ingredient.amount, ingredient.unit)


def ingredient_delta(name, adjective, category, delta, ingredient):
    return Ingredient(name, adjective, category, ingredient.amount*delta, ingredient.unit)


def ingredient_ignore(name, adjective, category, amount, unit, ingredient):
    return Ingredient(name, adjective, category, amount, unit)


# query/conversion functions

def categorize(ingredient):
    return


def convert_measure(ingredient):
    return


# substitution functions

def change_name(name, ingredient):
    ingredient.name = name
    if ingredient.adjective:
        return ingredient.adjective + ' ' + ingredient.name
    return ingredient.name


def change_adjective(adjective, ingredient):
    ingredient.adjective = adjective
    if ingredient.adjective:
        return ingredient.adjective + ' ' + ingredient.name
    return ingredient.name


def change_category(category, ingredient):
    ingredient.category = category
    if ingredient.adjective:
        return ingredient.adjective + ' ' + ingredient.name
    return ingredient.name


def change_amount(delta, ingredient):
    ingredient.amount *= delta
    if ingredient.adjective:
        return ingredient.adjective + ' ' + ingredient.name
    return ingredient.name


def change_unit(unit, ingredient):
    ingredient.unit = unit
    if ingredient.adjective:
        return ingredient.adjective + ' ' + ingredient.name
    return ingredient.name


# healthy substitutions dictionaries

healthy_substitutions_names = {
    'shortening': {'substitutions': [functools.partial(change_amount, 0.5)],
                   'additions': [functools.partial(ingredient_delta, 'applesauce', 'unsweetened', 'sauce', 1)],
                   'remove': None},
    'oil': {'substitutions': [functools.partial(change_adjective, 'olive')]},
    'butter': {'substitutions': [functools.partial(change_amount, 0.5)],
               'additions': [functools.partial(ingredient_delta, 'oil', 'olive', 'oil', 1)],
               'remove': None},
    'sugar': {'substitutions': [functools.partial(change_name, 'stevia')]},
    'salt': {'substitutions': [functools.partial(change_adjective, 'himalayan')]},
    'pasta': {'substitutions': [functools.partial(change_adjective, 'whole-wheat')]},
    'milk': {'substitutions': [functools.partial(change_adjective, 'almond')]},
    'cheese': {'substitutions': [functools.partial(change_amount, 0.5)]},
    'jelly': {'additions': [ingredient_base],
              'remove': None},
    'egg': {'substitutions': [functools.partial(change_adjective, 'substitute'),
                              functools.partial(change_amount, 0.25),
                              functools.partial(change_unit, 'cup')]},
    'rice': {'substitutions': [functools.partial(change_name, 'quinoa')]},
    'flour': {'substitutions': [functools.partial(change_adjective, 'whole-wheat')]},
    'chocolate': {'substitutions': [functools.partial(change_name, 'nibs'),
                                    functools.partial(change_adjective, 'cocoa')]},
    'beef': {'substitutions': [functools.partial(change_name, 'chicken')]},
    'steak': {'substitutions': [functools.partial(change_name, 'chicken')]},
    'bacon': {'substitutions': [functools.partial(change_adjective, 'turkey')]},
}
healthy_substitutions_adjectives = {
    'iceberg': {'substitutions': [functools.partial(change_adjective, 'romaine')]},
    'peanut': {'substitutions': [functools.partial(change_adjective, 'almond')]},
}
healthy_substitutions_categories = {
    'topping': {'remove': None},
    'condiment': {'remove': None},
    'vegetable': {'substitutions': [functools.partial(change_amount, 2)]},
}
healthy_substitutions_exceptions = {
    'peanut butter': {'substitutions': [functools.partial(change_adjective, 'almond')]},
    'sour cream': {'substitutions': [functools.partial(change_name, 'yogurt'),
                                     functools.partial(change_adjective, 'greek')]},
}
healthy_substitutions_methods = {
    'fry': 'saute'
}


# healthy baking substitutions dictionaries

healthy_baking_substitutions_names = {
    'shortening': {'substitutions': [functools.partial(change_amount, 0.5)],
                   'additions': [functools.partial(ingredient_delta, 'applesauce', 'unsweetened', 'sauce', 1)],
                   'remove': None},
    'oil': {'substitutions': [functools.partial(change_amount, 0.5)],
            'additions': [functools.partial(ingredient_delta, 'applesauce', 'unsweetened', 'sauce', 1)],
            'remove': None},
    'butter': {'substitutions': [functools.partial(change_amount, 0.5)],
               'additions': [functools.partial(ingredient_delta, 'applesauce', 'unsweetened', 'sauce', 1)],
               'remove': None},
    'sugar': {'substitutions': [functools.partial(change_name, 'stevia')]},
    'salt': {'substitutions': [functools.partial(change_adjective, 'himalayan')]},
    'milk': {'substitutions': [functools.partial(change_adjective, 'almond')]},
    'cheese': {'substitutions': [functools.partial(change_amount, 0.5)]},
    'jelly': {'additions': [ingredient_base],
              'remove': None},
    'egg': {'substitutions': [functools.partial(change_adjective, 'substitute'),
                              functools.partial(change_amount, 0.25),
                              functools.partial(change_unit, 'cup')]},
    'flour': {'substitutions': [functools.partial(change_adjective, 'whole-wheat')]},
    'chocolate': {'substitutions': [functools.partial(change_name, 'nibs'),
                                    functools.partial(change_adjective, 'cacao')]},
    'beef': {'substitutions': [functools.partial(change_name, 'chicken')]},
    'steak': {'substitutions': [functools.partial(change_name, 'chicken')]},
    'bacon': {'substitutions': [functools.partial(change_adjective, 'turkey')]},
}
healthy_baking_substitutions_adjectives = {
    'peanut': {'substitutions': [functools.partial(change_adjective, 'almond')]},
}
healthy_baking_substitutions_categories = {
    'topping': {'remove': None},
}
healthy_baking_substitutions_exceptions = {
    'peanut butter': {'substitutions': [functools.partial(change_adjective, 'almond')]},
}
healthy_baking_substitutions_methods = {
    'fry': 'bake'
}


# unhealthy substitutions dictionaries

unhealthy_substitutions_names = {
    'applesauce': {'substitutions': [functools.partial(change_amount, 3)],
                   'additions': [functools.partial(ingredient_delta, 'shortening', '', '', 1)],
                   'remove': None},
    'oil': {'substitutions': [functools.partial(change_amount, 3)],
            'additions': [functools.partial(ingredient_delta, 'butter', '', '', 1)],
            'remove': None},
    'stevia': {'substitutions': [functools.partial(change_name, 'sugar'),
                                 functools.partial(change_amount, 2)]},
    'salt': {'substitutions': [functools.partial(change_adjective, 'table'),
                               functools.partial(change_amount, 2)]},
    'pasta': {'substitutions': [functools.partial(change_adjective, '')]},
    'milk': {'substitutions': [functools.partial(change_adjective, 'whole')]},
    'cheese': {'substitutions': [functools.partial(change_amount, 2)]},
    'eggs': {'substitutions': [functools.partial(change_adjective, ''),
                               functools.partial(change_amount, 1),
                               functools.partial(change_unit, 'egg')]},
    'quinoa': {'substitutions': [functools.partial(change_name, 'rice'),
                                 functools.partial(change_adjective, 'white')]},
    'flour': {'substitutions': [functools.partial(change_adjective, '')]},
    'cacao': {'substitutions': [functools.partial(change_name, 'chocolate'),
                                functools.partial(change_adjective, '')]},
    'zoodles': {'additions': [functools.partial(ingredient_delta, 'pasta', '', '', 1)],
                'remove': None},
    'flaxseed': {'additions': [functools.partial(ingredient_delta, 'crumbs', 'bread', '', 1)],
                 'remove': None},
    'chicken': {'substitutions': [functools.partial(change_name, 'beef')]},
}
unhealthy_substitutions_adjectives = {
    'romaine': {'substitutions': [functools.partial(change_adjective, 'iceberg')]},
    'almond': {'substitutions': [functools.partial(change_adjective, 'peanut')]},
    'corn': {'substitutions': [functools.partial(change_adjective, 'flour')]},
    'fresh': {'substitutions': [functools.partial(change_adjective, 'canned')]},
}
unhealthy_substitutions_categories = {
    'vegetable': {'remove': None},
}
unhealthy_substitutions_exceptions = {
    'greek yogurt': {'substitutions': [functools.partial(change_name, 'sour'),
                                       functools.partial(change_adjective, 'cream')]},
}
unhealthy_substitutions_methods = {
    'saute': 'fry',
    'sauté': 'fry',
    'steam': 'fry',
    'grill': 'fry',
    'roast': 'fry',
    'bake': 'fry'
}


# unhealthy baking substitutions dictionaries

unhealthy_baking_substitutions_names = {
    'applesauce': {'substitutions': [functools.partial(change_amount, 3)],
                   'additions': [functools.partial(ingredient_delta, 'shortening', '', '', 1)],
                   'remove': None},
    'oil': {'substitutions': [functools.partial(change_amount, 3)],
            'additions': [functools.partial(ingredient_delta, 'butter', '', '', 1)],
            'remove': None},
    'stevia': {'substitutions': [functools.partial(change_name, 'sugar'),
                                 functools.partial(change_amount, 2)]},
    'salt': {'substitutions': [functools.partial(change_adjective, 'table'),
                               functools.partial(change_amount, 2)]},
    'pasta': {'substitutions': [functools.partial(change_adjective, '')]},
    'milk': {'substitutions': [functools.partial(change_adjective, 'whole')]},
    'cheese': {'substitutions': [functools.partial(change_amount, 2)]},
    'egg': {'substitutions': [functools.partial(change_adjective, ''),
                              functools.partial(change_amount, 1),
                              functools.partial(change_unit, 'egg')]},
    'quinoa': {'substitutions': [functools.partial(change_name, 'rice'),
                                 functools.partial(change_adjective, 'white')]},
    'flour': {'substitutions': [functools.partial(change_adjective, '')]},
    'cacao': {'substitutions': [functools.partial(change_name, 'chocolate'),
                                functools.partial(change_adjective, '')]},
    'zoodles': {'additions': [functools.partial(ingredient_delta, 'pasta', '', '', 1)],
                'remove': None},
    'flaxseed': {'additions': [functools.partial(ingredient_delta, 'crumbs', 'bread', '', 1)],
                 'remove': None},
    'chicken': {'substitutions': [functools.partial(change_name, 'beef')]},
}
unhealthy_baking_substitutions_adjectives = {
    'romaine': {'substitutions': [functools.partial(change_adjective, 'iceberg')]},
    'almond': {'substitutions': [functools.partial(change_adjective, 'peanut')]},
    'corn': {'substitutions': [functools.partial(change_adjective, 'flour')]},
    'fresh': {'substitutions': [functools.partial(change_adjective, 'canned')]},
}
unhealthy_baking_substitutions_categories = {
    'vegetable': {'remove': None},
}
unhealthy_baking_substitutions_exceptions = {
    'greek yogurt': {'substitutions': [functools.partial(change_name, 'sour'),
                                       functools.partial(change_adjective, 'cream')]},
}
unhealthy_baking_substitutions_methods = {
    'saute': 'fry',
    'sauté': 'fry',
    'steam': 'fry',
    'grill': 'fry',
    'roast': 'fry'
}


# vegetarian substitutions dictionaries

vegetarian_substitutions_names = {
    'broth': {'substitutions': [functools.partial(change_adjective, 'vegetable'),
                                functools.partial(change_category, 'broth')]},
}
vegetarian_substitutions_adjectives = {}
vegetarian_substitutions_categories = {
    'chicken': {'substitutions': [functools.partial(change_name, 'eggplant'),
                                  functools.partial(change_adjective, None),
                                  functools.partial(change_category, 'vegetable')]},
    'pork': {'substitutions': [functools.partial(change_name, 'tofu'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'curd')]},
    'beef': {'substitutions': [functools.partial(change_name, 'lentils'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'vegetable')]},
    'sausage': {'substitutions': [functools.partial(change_name, 'seitan'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'vegetable')]},
    'steak': {'substitutions': [functools.partial(change_name, 'mushroom'),
                                functools.partial(change_adjective, 'portobello'),
                                functools.partial(change_category, 'vegetable')]},
    'bacon': {'substitutions': [functools.partial(change_adjective, 'seitan'),
                                functools.partial(change_adjective, None),
                                functools.partial(change_category, 'vegetable')]},
    'fish': {'substitutions': [functools.partial(change_name, 'tofu'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'curd')]},
    'crawfish': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'crayfish': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'tuna': {'substitutions': [functools.partial(change_name, 'tofuna'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'curd')]},
    'trout': {'substitutions': [functools.partial(change_name, 'tempeh'),
                                functools.partial(change_adjective, None),
                                functools.partial(change_category, 'vegetable')]},
    'carp': {'substitutions': [functools.partial(change_name, 'tempeh'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'vegetable')]},
    'flounder': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'bass': {'substitutions': [functools.partial(change_name, 'tofu'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'curd')]},
    'sturgeon': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'shrimp': {'substitutions': [functools.partial(change_name, 'shrimp'),
                                 functools.partial(change_adjective, 'vegan'),
                                 functools.partial(change_category, 'curd')]},
    'salmon': {'substitutions': [functools.partial(change_name, 'salmon'),
                                 functools.partial(change_adjective, 'vegan'),
                                 functools.partial(change_category, 'vegetable')]},
    'lobster': {'substitutions': [functools.partial(change_name, 'lobster'),
                                  functools.partial(change_adjective, 'vegan'),
                                  functools.partial(change_category, 'curd')]},
    'scallops': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'lamb': {'substitutions': [functools.partial(change_name, 'seitan'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'vegetable')]},
    'crab': {'substitutions': [functools.partial(change_name, 'crab'),
                               functools.partial(change_adjective, 'vegan'),
                               functools.partial(change_category, 'vegetable')]},
    'turkey': {'substitutions': [functools.partial(change_name, 'tofurkey'),
                                 functools.partial(change_adjective, None),
                                 functools.partial(change_category, 'curd')]},
    'duck': {'substitutions': [functools.partial(change_name, 'duck'),
                               functools.partial(change_adjective, 'mock'),
                               functools.partial(change_category, 'vegetable')]},
    'liver': {'substitutions': [functools.partial(change_name, 'liver'),
                                functools.partial(change_adjective, 'mock'),
                                functools.partial(change_category, 'vegetable')]},
    'ribs': {'substitutions': [functools.partial(change_name, 'seitan'),
                               functools.partial(change_adjective, None),
                               functools.partial(change_category, 'vegetable')]},
    'pheasant': {'substitutions': [functools.partial(change_name, 'eggplant'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'vegetable')]},
    'quail': {'substitutions': [functools.partial(change_name, 'eggplant'),
                                functools.partial(change_adjective, None),
                                functools.partial(change_category, 'vegetable')]},
    'goose': {'substitutions': [functools.partial(change_name, 'eggplant'),
                                functools.partial(change_adjective, None),
                                functools.partial(change_category, 'vegetable')]},
    'escargot': {'substitutions': [functools.partial(change_name, 'tofu'),
                                   functools.partial(change_adjective, None),
                                   functools.partial(change_category, 'curd')]},
    'snail': {'substitutions': [functools.partial(change_name, 'tofu'),
                                functools.partial(change_adjective, None),
                                functools.partial(change_category, 'curd')]},

}
vegetarian_substitutions_exceptions = {}


# non-vegetarian substitutions dictionaries

non_vegetarian_substitutions_names = {
    'eggplant': {'substitutions': [functools.partial(change_name, 'chicken'),
                                   functools.partial(change_adjective, 'fried'),
                                   functools.partial(change_category, 'meat')]},
    'tofu': {'substitutions': [functools.partial(change_name, 'pork'),
                               functools.partial(change_category, 'meat')]},
    'lentils': {'substitutions': [functools.partial(change_name, 'beef'),
                                  functools.partial(change_category, 'meat')]},
    'mushroom': {'substitutions': [functools.partial(change_name, 'steak'),
                                   functools.partial(change_adjective, ''),
                                   functools.partial(change_category, 'meat')]},
    'seitan': {'substitutions': [functools.partial(change_name, 'bacon'),
                                 functools.partial(change_category, 'meat')]},
    'tempeh': {'substitutions': [functools.partial(change_name, 'fish'),
                                 functools.partial(change_category, 'meat')]},
}
non_vegetarian_substitutions_adjectives = {}
non_vegetarian_substitutions_categories = {}
non_vegetarian_substitutions_exceptions = {}


# thai substitutions dictionaries

thai_substitutions_names = {
    'salt': {'substitutions': [functools.partial(change_name, 'fish sauce'),
                               functools.partial(change_adjective, 'thai'),
                               functools.partial(change_amount, 1),
                               functools.partial(change_unit, 'tablespoon')]},
    'broccoli': {'substitutions': [functools.partial(change_adjective, 'chinese')]},
    'pasta': {'substitutions': [functools.partial(change_adjective, 'rice'),
                                functools.partial(change_name, 'noodles')]},
    'noodles': {'substitutions': [functools.partial(change_adjective, 'rice')]},
    'milk': {'substitutions': [functools.partial(change_adjective, 'coconut')]},
    'cream': {'substitutions': [functools.partial(change_adjective, 'coconut'),
                                functools.partial(change_name, 'milk')]},
    'onions': {'substitutions': [functools.partial(change_name, 'shallots')]},
    'onion': {'substitutions': [functools.partial(change_name, 'shallot')]},
    'basil': {'substitutions': [functools.partial(change_adjective, 'thai')]},
    'sugar': {'substitutions': [functools.partial(change_adjective, 'palm')]},
    'apple': {'substitutions': [functools.partial(change_name, 'mango'),
                                functools.partial(change_adjective, 'green')]},
    'turnip': {'substitutions': [functools.partial(change_name, 'radish'),
                                 functools.partial(change_adjective, 'white')]},
}
thai_substitutions_adjectives = {
    'whole-wheat': {'substitutions': [functools.partial(change_adjective, 'rice')]},
}
thai_substitutions_categories = {
    'pepper': {'substitutions': [functools.partial(change_adjective, 'chili')]}
}
thai_substitutions_exceptions = {
    'soy sauce': [functools.partial(change_name, 'fish sauce'),
                  functools.partial(change_adjective, 'thai')],
    'lemon zest': [functools.partial(change_name, 'lemongrass'),
                   functools.partial(change_adjective, None),
                   functools.partial(change_category, 'herb')],
    'large onion': {'substitutions': [functools.partial(change_name, 'shallots')]}
}

# mediterranean substitutions dictionaries

mediterranean_substitutions_names = {
    'broth': {'substitutions': [functools.partial(change_adjective, 'vegetable'),
                                functools.partial(change_category, 'broth')]},
    'tofu': {'substitutions': [functools.partial(change_name, 'fish'),
                               functools.partial(change_category, 'meat')]},
    'butter': {'substitutions': [functools.partial(change_name, 'olive oil'),
                                 functools.partial(change_category, 'healthy_fats')]},
    'soybean oil': {'substitutions': [functools.partial(change_name, 'sesame oil')]},
    'corn oil': {'substitutions': [functools.partial(change_name, 'olive oil')]},
    'vegetable oil': {'substitutions': [functools.partial(change_name, 'olive oil')]},
    'cottonseed oil': {'substitutions': [functools.partial(change_name, 'flaxseed oil')]},
    'bread': {'substitutions': [functools.partial(change_name, 'pita')]},
    'jelly': {'substitutions': [functools.partial(change_name, 'berries'),
                                functools.partial(change_adjective, 'fresh')]},
    'rice': {'substitutions': [functools.partial(change_adjective, 'wild'),
                               functools.partial(change_category, 'healthy_grains')]},
    'pasta': {'substitutions': [functools.partial(change_adjective, 'whole-wheat'),
                                functools.partial(change_category, 'healthy_grains')]},
    'flour': {'substitutions': [functools.partial(change_adjective, 'whole-wheat')]},
}
mediterranean_substitutions_adjectives = {}
mediterranean_substitutions_categories = {
    'unhealthy_fats': {'substitutions': [functools.partial(change_name, 'olive oil'),
                                         functools.partial(change_category, 'healthy_fats')]},
    'unhealthy_dairy': {'substitutions': [functools.partial(change_name, 'yogurt'),
                                          functools.partial(change_adjective, 'greek'),
                                          functools.partial(change_category, 'healthy_dairy')]},
    'beef': {'substitutions': [functools.partial(change_name, 'salmon'),
                               functools.partial(change_adjective, 'fillet')]},
    'chicken': {'substitutions': [functools.partial(change_name, 'tuna'),
                                  functools.partial(change_adjective, 'fillet')]},
    'turkey': {'substitutions': [functools.partial(change_name, 'beans'),
                                 functools.partial(change_adjective, None)]},
    'pork': {'substitutions': [functools.partial(change_name, 'trout'),
                               functools.partial(change_adjective, 'fillet')]},
    'bacon': {'substitutions': [functools.partial(change_name, 'salmon'),
                                functools.partial(change_adjective, None)]},
    'sausage': {'substitutions': [functools.partial(change_name, 'lentils')]},
}
mediterranean_substitutions_exceptions = {}


# helper functions

def add_ingredient(ingredient_text):
    global INGREDIENT_CATEGORIES
    global SYNONYMS
    adjective = None
    category = None
    amount = None
    unit = None
    ingredient_parts = ingredient_text.split(', ')
    ingredient = ingredient_parts[0]
    if len(ingredient_parts) > 1:
        ingredient_style = ingredient_parts[1]
    if 'to taste' in ingredient:

        print('\ningred name:', ingredient.replace(' to taste', ''))

        return Ingredient(ingredient.replace(' to taste', ''), None, None, None, None)
    ingredient_words = ingredient.split()
    name = ingredient_words[-1]
    ingredient_words = ingredient_words[:-1]
    if ingredient_words and ingredient_words[0][0].isdigit():
        if '/' in ingredient_words[0]:
            amount_split = ingredient_words[0].split('/')
            amount = int(amount_split[0]) / int(amount_split[1])
        else:
            amount = float(ingredient_words[0])
        ingredient_words = ingredient_words[1:]
    if ingredient_words and amount:
        if ingredient_words[0][0] == '(' and ingredient_words[0][1].isdigit():
            amount = ingredient_words[0][1:]
            unit = ingredient_words[1][:-1]
            ingredient_words = ingredient_words[2:]
        else:
            pos = set()
            for synset in nltk.corpus.wordnet.synsets(ingredient_words[0]):
                if synset.name().split('.')[0] == ingredient_words[0]:
                    pos.add(synset.pos())
            if 'a' not in pos and 's' not in pos:
                unit = ingredient_words[0]
                ingredient_words = ingredient_words[1:]
    for word in ingredient_words:
        pos = set()
        for synset in nltk.corpus.wordnet.synsets(word):
            if synset.name().split('.')[0] == word:
                pos.add(synset.pos())
        if not pos or 'a' in pos or 's' in pos or 'v' in pos:
            if not adjective:
                adjective = word
            else:
                adjective += ' ' + word
            ingredient_words = ingredient_words[1:]
        else:
            break
    # if ingredient_words:
    #     prefix = ''
    #     for word in ingredient_words:
    #         prefix += word + ' '
    #     name = prefix + name

    for word in ingredient_words:
        if not adjective:
            adjective = word
        else:
            adjective += ' ' + word

    if name in SYNONYMS:
        name = SYNONYMS[name]
    full_name = name
    if adjective:
        full_name = adjective + name
    for meat in INGREDIENT_CATEGORIES['meat']:
        if meat in full_name:
            category = meat

    for key, val in INGREDIENT_CATEGORIES.items():
        if (full_name in val or name in val) and category is None:
            category = key

    print('\ningred amt:', str(amount))
    print('ingred unit:', unit)
    print('ingred adj:', adjective)
    print('ingred name:', name)
    print('ingred cat:', category)

    return Ingredient(name, adjective, category, amount, unit)


def make_substitutions_with(ingredients, ingredient_switches, names, adjectives, categories, exceptions, vegetarian):
    global INGREDIENT_CATEGORIES
    added_ingredients = []
    removed_ingredients = []
    for ingredient in ingredients:
        name = ingredient.name
        full_name = name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if full_name in exceptions:
            removed, new_name = make_substitutions(ingredient, exceptions[full_name], added_ingredients)
            ingredient_switches[full_name] = new_name
            ingredient_switches[name] = ingredient.name
            if removed:
                removed_ingredients.append(ingredient)
            continue
        if name in names:
            removed, new_name = make_substitutions(ingredient, names[name], added_ingredients)
            ingredient_switches[full_name] = new_name
            ingredient_switches[name] = ingredient.name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.adjective in adjectives:
            removed, new_name = make_substitutions(ingredient, adjectives[ingredient.adjective], added_ingredients)
            ingredient_switches[full_name] = new_name
            ingredient_switches[name] = ingredient.name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.category in categories:
            category = ingredient.category
            removed, new_name = make_substitutions(ingredient, categories[category], added_ingredients)
            ingredient_switches[full_name] = new_name
            ingredient_switches[name] = ingredient.name
            if vegetarian and category in INGREDIENT_CATEGORIES['meat']:
                ingredient_switches[' ' + category] = ''
                ingredient_switches['meat'] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    for added_ingredient in added_ingredients:
        combined = False
        for ingredient in ingredients:
            if ingredient.name == added_ingredient.name and ingredient.adjective == added_ingredient.adjective:
                ingredient.amount += added_ingredient.amount
                combined = True
                break
        if not combined:
            ingredients.append(added_ingredient)


def make_substitutions(ingredient, substitutions, added_ingredients):
    new_name = ''
    if 'substitutions' in substitutions:
        for substitution in substitutions['substitutions']:
            new_name = substitution(ingredient)
    if 'additions' in substitutions:
        for addition in substitutions['additions']:
            new_ingredient = addition(ingredient)
            added_ingredients.append(new_ingredient)
    if 'remove' in substitutions:
        return True, ''
    return False, new_name


if __name__ == '__main__':
    while True:
        # url = input('Please provide a recipe URL: ')

        url = 'https://www.allrecipes.com/recipe/173906/cajun-roasted-pork-loin/'
        # url = 'https://www.allrecipes.com/recipe/269944/shrimp-and-smoked-sausage-jambalaya/'

        if len(url) > 40 and url[:34] == 'https://www.allrecipes.com/recipe/':
            try:
                # take url and load recipe using beautiful soup
                soup = BeautifulSoup(urllib.request.urlopen(url), 'html.parser')
                # instantiate recipe object using soup
                recipe = Recipe(soup)
                break
            except Exception as e:
                print(e)
        print('Invalid input, please try again.\n')
    while True:
        # transformation = input('\nHow would you like to transform your recipe? Type "healthy", "unhealthy", "vegetarian", "meatify", "mediterranean", or "thai": ')

        transformation = 'mediterranean'

        if transformation == 'healthy':
            recipe.make_healthy()
            break
        elif transformation == 'unhealthy':
            recipe.make_unhealthy()
            break
        elif transformation == 'vegetarian':
            recipe.make_vegetarian()
            break
        elif transformation == 'meatify':
            recipe.make_non_vegetarian()
            break
        elif transformation == 'thai':
            recipe.make_thai()
            break
        elif transformation == 'mediterranean':
            recipe.make_mediterranean()
            break
        print('Invalid input, please try again.')
