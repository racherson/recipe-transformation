import collections
import functools
import json
import nltk
import pymongo
import urllib.request
from bs4 import BeautifulSoup
from pprint import pprint


# TODOs

# TODO: merge ingredients if they are in same step
# TODO: deal with salt...
# TODO: set ingredient category in add_ingredient
# TODO: lemmatize when parsing steps for methods so tense is taken into consideration
# TODO: parametrize substitution functions with dictionary arguments for less code repetition
# TODO: parametrize recipe transformation with user input


# global variables

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
stopwords = nltk.corpus.stopwords.words('english')
punctuation = [',', '.', '!', '?', '(', ')']
stopwords.extend(punctuation)
METHODS = ['add', 'use', 'blend', 'cut', 'strain', 'roast', 'slice', 'flip', 'baste', 'simmer', 'grate', 'drain', 'saute', 'broil', 'boil', 'poach', 'bake', 'grill', 'fry', 'bake', 'heat', 'mix', 'chop', 'grate', 'stir', 'shake', 'mince', 'crush', 'squeeze', 'dice', 'rub', 'cook']
TOOLS = ['pan', 'grater', 'whisk', 'pot', 'spatula', 'tong', 'oven', 'knife']


# categorized foods (found at https://github.com/olivergoodman/food-recipes/blob/master/transforms.py)

ingredient_categories = {
    'healthy_fats': ['olive oil', 'sunflower oil', 'soybean oil', 'corn oil',  'sesame oil',  'peanut oil'],
    'unhealthy_fats': ['butter', 'lard', 'shortening', 'canola oil', 'margarine',  'coconut oil',  'tallow',  'cream', 'milk fat',  'palm oil',  'palm kemel oil',  'chicken fat',  'hydrogenated oils'],
    'healthy_protein': ['peas',  'beans', 'eggs', 'crab', 'fish', 'chicken', 'tofu', 'liver', 'turkey'],
    'unhealthy_protein': ['ground beef', 'beef', 'pork', 'lamb'],
    'meat': ['ground beef', 'beef', 'pork', 'lamb', 'crab', 'fish', 'chicken', 'turkey', 'liver'],
    'healthy_dairy': ['fat free milk', 'low fat milk', 'yogurt',  'low fat cheese'],
    'unhealthy_dairy': ['reduced-fat milk', 'cream cheese', 'whole milk', 'butter', 'cheese', 'whipped cream', 'sour cream'],
    'healthy_salts': ['low sodium soy sauce', 'sea salt', 'kosher salt'],
    'unhealthy_salts': ['soy sauce', 'table salt', 'salt'],
    'healthy_grains': ['oat cereal', 'wild rice', 'oatmeal', 'whole rye', 'buckwheat', 'rolled oats', 'quinoa','bulgur', 'millet', 'brown rice', 'whole wheat pasta'],
    'unhealthy_grains': ['macaroni', 'noodles', 'spaghetti', 'white rice', 'white bread', 'regular white pasta'],
    'healthy_sugars': ['real fruit jam', 'fruit juice concentrates', 'monk fruit extract', 'cane sugar', 'molasses', 'brown rice syrup' 'stevia', 'honey', 'maple syrup', 'agave syrup', 'coconut sugar', 'date sugar', 'sugar alcohols', 'brown sugar'],
    'unhealthy_sugars': ['aspartame', 'acesulfame K', 'sucralose', 'white sugar', 'corn syrup', 'chocolate syrup']
}


# recipe class definition

class Recipe:
    def __init__(self, url):
        # take url and load recipe using beautiful soup
        self.url = url
        html = urllib.request.urlopen(url)
        self.soup = BeautifulSoup(html, 'html.parser')
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
        # initialize ingredient switches dictionary
        self.ingredient_switches = {}
        # print recipe
        self.print_recipe()

    def get_steps(self):
        # get steps from soup
        directions = self.soup.find('ol', class_='list-numbers recipe-directions__list')
        steps_elements = directions('li')
        steps = []
        for count, step_element in enumerate(steps_elements):
            step_text = str(count+1) + '. ' + step_element.find('span').string.strip()
            steps.append(Step(step_text, self.ingredients))
        return steps

    def get_tools_methods(self):
        global stopwords
        global TOOLS
        global METHODS
        tools = set()  # unique set
        methods_counter = collections.Counter()  # frequency mapping
        for step in self.steps:
            tokens = nltk.word_tokenize(step.text)
            tokens = [token.lower() for token in tokens if token not in stopwords]
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
        global punctuation
        for step in self.steps:
            tokens = nltk.word_tokenize(step.text)
            altered_step_text = ''
            for token in tokens:
                if token == '(':
                    altered_step_text += token
                elif token in punctuation:
                    altered_step_text = altered_step_text[:-1] + token + ' '
                elif token.lower() in self.ingredient_switches:
                    altered_step_text += self.ingredient_switches[token.lower()] + ' '
                else:
                    altered_step_text += token + ' '
            step.text = altered_step_text[:-1]

    def make_healthy(self):
        print('Making healthy...')
        for step in self.steps:
            make_healthy_substitutions(step.ingredients, self.ingredient_switches, self.bake)
        self.alter_steps()
        print('Altered Steps:')
        for step in self.steps:
            print(step)

    def make_unhealthy(self):
        print('Making unhealthy...')
        for step in self.steps:
            make_unhealthy_substitutions(step.ingredients, self.ingredient_switches, self.bake, self.steps)
        self.alter_steps()
        next_count = int(self.steps[-1].text[0]) + 1
        if not self.bake:
            more_salt = Ingredient("salt", "extra", "topping", "", "")
            self.ingredients.append(more_salt)
            step_text = str(next_count) + ". " + "Sprinkle a lot of extra salt over the whole meal."
            new_step = Step(step_text, [more_salt])
            new_step.methods = ["sprinkle"]
            self.steps.append(new_step)
        else:
            add_frosting = Ingredient("frosting", "chocolate", "topping", 2, "cups")
            self.ingredients.append(add_frosting)
            step_text = str(next_count) + ". " + "Spread frosting over everything."
            new_step = Step(step_text, [add_frosting])
            new_step.methods = ["spread"]
            self.steps.append(new_step)
        print('Altered Ingredients:')
        for ingredient in self.ingredients:
            print(ingredient)
        print('Altered Steps:')
        for step in self.steps:
            print(step)

    def make_vegetarian(self):
        print('Making vegetarian...')
        for step in self.steps:
            make_vegetarian_substitutions(step.ingredients, self.ingredient_switches)
        self.alter_steps()
        print('Altered Steps:')
        for step in self.steps:
            print(step)

    def make_non_vegetarian(self):
        print('Making non-vegetarian...')
        for step in self.steps:
            make_non_vegetarian_substitutions(step.ingredients, self.ingredient_switches)
        self.alter_steps()
        print('Altered Steps:')
        for step in self.steps:
            print(step)

    def make_thai(self):
        print('Making Thai...')
        for step in self.steps:
            make_thai_substitutions(step.ingredients, self.ingredient_switches)
        self.alter_steps()
        print('Altered Steps:')
        for step in self.steps:
            print(step)

    def print_recipe(self):
        print('Name: ', self.name)
        print('Ingredients:')
        for ingredient in self.ingredients:
            print(ingredient)
        print('Tools: ', self.tools)
        print('Primary Method: ', self.primary_method)
        print('Other Methods: ', self.other_methods)
        print('Baking?: ', self.bake)
        print('Steps:')
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
        for ingredient in ingredients:
            full_name = ingredient.name
            if ingredient.adjective:
                full_name = ingredient.adjective + ' ' + full_name
            if full_name in step_text.lower():
                self.ingredients.append(ingredient)

    def __str__(self):
        # return self.text
        output = self.text + '\n' + 'Ingredients:  '
        for ingredient in self.ingredients:
            output += str(ingredient) + ', '
        output = output[:-2] + '\n' + 'Methods:  '
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


# query/conversion functions

def categorize(ingredient):
    return


def convert_measure(ingredient):
    return


# substitution functions

def change_name(name, ingredient):
    ingredient.name = name
    return ingredient.name


def change_adjective(adjective, ingredient):
    ingredient.adjective = adjective
    return ingredient.name


def change_category(category, ingredient):
    ingredient.category = category
    return ingredient.name


def change_amount(delta, ingredient):
    ingredient.amount *= delta
    return ingredient.name


def change_unit(unit, ingredient):
    ingredient.unit = unit
    return ingredient.name


def change_method(method):
    pass


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


# baking healthy substitutions dictionaries

baking_healthy_substitutions_names = {
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
}
baking_healthy_substitutions_adjectives = {
    'peanut': {'substitutions': [functools.partial(change_adjective, 'almond')]}
}
baking_healthy_substitutions_categories = {
    'topping': {'remove': None}
}
baking_healthy_substitutions_exceptions = {
    'peanut butter': {'substitutions': [functools.partial(change_adjective, 'almond')]}
}

# unhealthy substitutions dictionaries
unhealthy_substitutions_names = {
    "applesauce": {"substitutions": [functools.partial(change_amount, 3)],
                   "additions": [functools.partial(ingredient_delta, "shortening", "", "", 1)],
                   "remove": None},
    "oil": {"substitutions": [functools.partial(change_amount, 3)],
               "additions": [functools.partial(ingredient_delta, "butter", "", "", 1)],
               "remove": None},
    "stevia": {"substitutions": [functools.partial(change_name, "sugar"),
                                 functools.partial(change_amount, 2)]},
    "salt": {"substitutions": [functools.partial(change_adjective, "table"),
                               functools.partial(change_amount, 2)]},
    "pasta": {"substitutions": [functools.partial(change_adjective, "")]},
    "milk": {"substitutions": [functools.partial(change_adjective, "whole")]},
    "cheese": {"substitutions": [functools.partial(change_amount, 2)]},
    "eggs": {"substitutions": [functools.partial(change_adjective, ""),
                              functools.partial(change_amount, 1),
                              functools.partial(change_unit, "egg")]},
    "quinoa": {"substitutions": [functools.partial(change_name, "rice"),
                                 functools.partial(change_adjective, "white")]},
    "flour": {"substitutions": [functools.partial(change_adjective, "")]},
    "cacao": {"substitutions": [functools.partial(change_name, "chocolate"),
                                    functools.partial(change_adjective, "")]},
    "zoodles": {"additions": [functools.partial(ingredient_delta, "pasta", "", "", 1)],
               "remove": None},
    "flaxseed": {"additions": [functools.partial(ingredient_delta, "crumbs", "bread", "", 1)],
               "remove": None},
}

unhealthy_substitutions_adjectives = {
    "romaine": {"substitutions": [functools.partial(change_adjective, "iceberg")]},
    "almond": {"substitutions": [functools.partial(change_adjective, "peanut")]},
    "corn": {"substitutions": [functools.partial(change_adjective, "flour")]},
    "fresh": {"substitutions": [functools.partial(change_adjective, "canned")]},
}
unhealthy_substitutions_categories = {
    "vegetable": {"remove": None},
}
unhealthy_substitutions_exceptions = {
    "greek yogurt": {"substitutions": [functools.partial(change_name, "sour"),
                                       functools.partial(change_adjective, "cream")]},
}

unhealthy_substitutions_methods = {}

# baking unhealthy substitutions dictionaries
baking_unhealthy_substitutions_names = {
    "applesauce": {"substitutions": [functools.partial(change_amount, 3)],
                   "additions": [functools.partial(ingredient_delta, "shortening", "", "", 1)],
                   "remove": None},
    "oil": {"substitutions": [functools.partial(change_amount, 3)],
               "additions": [functools.partial(ingredient_delta, "butter", "", "", 1)],
               "remove": None},
    "stevia": {"substitutions": [functools.partial(change_name, "sugar"),
                                 functools.partial(change_amount, 2)]},
    "salt": {"substitutions": [functools.partial(change_adjective, "table"),
                               functools.partial(change_amount, 2)]},
    "pasta": {"substitutions": [functools.partial(change_adjective, "")]},
    "milk": {"substitutions": [functools.partial(change_adjective, "whole")]},
    "cheese": {"substitutions": [functools.partial(change_amount, 2)]},
    "egg": {"substitutions": [functools.partial(change_adjective, ""),
                              functools.partial(change_amount, 1),
                              functools.partial(change_unit, "egg")]},
    "quinoa": {"substitutions": [functools.partial(change_name, "rice"),
                                 functools.partial(change_adjective, "white")]},
    "flour": {"substitutions": [functools.partial(change_adjective, "")]},
    "cacao": {"substitutions": [functools.partial(change_name, "chocolate"),
                                functools.partial(change_adjective, "")]},
    "zoodles": {"additions": [functools.partial(ingredient_delta, "pasta", "", "", 1)],
               "remove": None},
    "flaxseed": {"additions": [functools.partial(ingredient_delta, "crumbs", "bread", "", 1)],
               "remove": None},
}
baking_unhealthy_substitutions_adjectives = {
    "romaine": {"substitutions": [functools.partial(change_adjective, "iceberg")]},
    "almond": {"substitutions": [functools.partial(change_adjective, "peanut")]},
    "corn": {"substitutions": [functools.partial(change_adjective, "flour")]},
    "fresh": {"substitutions": [functools.partial(change_adjective, "canned")]}
}
baking_unhealthy_substitutions_categories = {
    "vegetable": {"remove": None}
}
baking_unhealthy_substitutions_exceptions = {
    "greek yogurt": {"substitutions": [functools.partial(change_name, "sour"),
                                       functools.partial(change_adjective, "cream")]}
}

# vegetarian substitutions dictionaries

vegetarian_substitutions_names = {
    'chicken': {'substitutions': [functools.partial(change_name, 'eggplant')]},
    'pork': {'substitutions': [functools.partial(change_name, 'tofu')]},
    'beef': {'substitutions': [functools.partial(change_name, 'lentils')]},
    'steak': {'substitutions': [functools.partial(change_name, 'mushroom'),
                                functools.partial(change_adjective, 'portobello')]},
    'bacon': {'substitutions': [functools.partial(change_adjective, 'seitan')]},
    'fish': {'substitutions': [functools.partial(change_name, 'tofu')]}
}
vegetarian_substitutions_adjectives = {
    'chicken': {'substitutions': [functools.partial(change_adjective, 'vegetable')]},
    'pork': {'substitutions': [functools.partial(change_adjective, 'vegetable')]},
    'beef': {'substitutions': [functools.partial(change_adjective, 'vegetable')]},
}
vegetarian_substitutions_categories = {}
vegetarian_substitutions_exceptions = {}

# unvegetarian substitutions dictionaries

unvegetarian_substitutions_names = {
    "eggplant": {"substitutions": [functools.partial(change_name, "chicken"),
                                   functools.partial(change_adjective, "fried")]},
    "tofu": {"substitutions": [functools.partial(change_name, "pork")]},
    "lentils": {"substitutions": [functools.partial(change_name, "beef")]},
    "mushroom": {"substitutions": [functools.partial(change_name, "steak"),
                                functools.partial(change_adjective, "")]},
    "seitan": {"substitutions": [functools.partial(change_adjective, "bacon")]},
}


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
    'onions': {'substitutions': [functools.partial(change_name, 'shallots')]},
    'basil': {'substitutions': [functools.partial(change_adjective, 'thai')]},
}
thai_substitutions_adjectives = {
    'whole-wheat': {'substitutions': [functools.partial(change_adjective, 'rice')]}
}
thai_substitutions_categories = {
    'sauce': {'substitutions': [functools.partial(change_adjective, 'thai'),
                                functools.partial(change_name, 'curry paste')]}
}
thai_substitutions_exceptions = {}


# helper functions

def add_ingredient(ingredient_text):
    adjective = None
    category = None
    amount = None
    unit = None
    ingredient_parts = ingredient_text.split(', ')
    ingredient = ingredient_parts[0]
    if len(ingredient_parts) > 1:
        ingredient_style = ingredient_parts[1]
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
    if ingredient_words:
        unit = ingredient_words[0]
        ingredient_words = ingredient_words[1:]
    if ingredient_words:
        adjective = ingredient_words[0]
        ingredient_words = ingredient_words[1:]
        for word in ingredient_words:
            adjective += ' ' + word
    return Ingredient(name, adjective, category, amount, unit)


def make_healthy_substitutions(ingredients, ingredient_switches, bake):
    global healthy_substitutions_names
    global healthy_substitutions_adjectives
    global healthy_substitutions_categories
    global healthy_substitutions_exceptions
    global baking_healthy_substitutions_names
    global baking_healthy_substitutions_adjectives
    global baking_healthy_substitutions_categories
    global baking_healthy_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    # loop through ingredients and make substitutions
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if bake is True:
            if full_name in baking_healthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_healthy_substitutions_exceptions[full_name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                continue
            if ingredient.name in baking_healthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_healthy_substitutions_names[ingredient.name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in baking_healthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_healthy_substitutions_adjectives[ingredient.adjective],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in baking_healthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_healthy_substitutions_categories[ingredient.category],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
        else:
            if full_name in healthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient,
                                                       healthy_substitutions_exceptions[full_name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                continue
            if ingredient.name in healthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient,
                                                       healthy_substitutions_names[ingredient.name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in healthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient,
                                                       healthy_substitutions_adjectives[ingredient.adjective],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in healthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient,
                                                       healthy_substitutions_categories[ingredient.category],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients


def make_unhealthy_substitutions(ingredients, ingredient_switches, bake, steps):
    global unhealthy_substitutions_names
    global unhealthy_substitutions_adjectives
    global unhealthy_substitutions_categories
    global unhealthy_substitutions_exceptions
    global baking_unhealthy_substitutions_names
    global baking_unhealthy_substitutions_adjectives
    global baking_unhealthy_substitutions_categories
    global baking_unhealthy_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    # loop through ingredients and make substitutions
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if bake is True:
            if full_name in baking_unhealthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_unhealthy_substitutions_exceptions[full_name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                continue
            if ingredient.name in baking_unhealthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_unhealthy_substitutions_names[ingredient.name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in baking_unhealthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_unhealthy_substitutions_adjectives[ingredient.adjective],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in baking_unhealthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient,
                                                       baking_unhealthy_substitutions_categories[ingredient.category],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue

        else:
            if full_name in unhealthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient,
                                                       unhealthy_substitutions_exceptions[full_name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                continue
            if ingredient.name in unhealthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient,
                                                       unhealthy_substitutions_names[ingredient.name],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in unhealthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient,
                                                       unhealthy_substitutions_adjectives[ingredient.adjective],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in unhealthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient,
                                                       unhealthy_substitutions_categories[ingredient.category],
                                                       added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue

    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients


def make_vegetarian_substitutions(ingredients, ingredient_switches):
    global vegetarian_substitutions_names
    global vegetarian_substitutions_adjectives
    global vegetarian_substitutions_categories
    global vegetarian_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if full_name in vegetarian_substitutions_exceptions:
            removed, new_name = make_substitutions(ingredient,
                                                   vegetarian_substitutions_exceptions[full_name],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            continue
        if ingredient.name in vegetarian_substitutions_names:
            removed, new_name = make_substitutions(ingredient,
                                                   vegetarian_substitutions_names[ingredient.name],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.adjective in vegetarian_substitutions_adjectives:
            removed, new_name = make_substitutions(ingredient,
                                                   vegetarian_substitutions_adjectives[ingredient.adjective],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.category in vegetarian_substitutions_categories:
            removed, new_name = make_substitutions(ingredient,
                                                   vegetarian_substitutions_categories[ingredient.category],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients


def make_non_vegetarian_substitutions(ingredients, ingredient_switches):
    global unvegetarian_substitutions_names
    added_ingredients = []
    removed_ingredients = []
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if ingredient.name in unvegetarian_substitutions_names:
            removed, new_name = make_substitutions(ingredient,
                                                   unvegetarian_substitutions_names[ingredient.name],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients


def make_thai_substitutions(ingredients, ingredient_switches):
    global thai_substitutions_names
    global thai_substitutions_adjectives
    global thai_substitutions_categories
    global thai_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + ' ' + full_name
        if full_name in thai_substitutions_exceptions:
            removed, new_name = make_substitutions(ingredient,
                                                   thai_substitutions_exceptions[full_name],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            continue
        if ingredient.name in thai_substitutions_names:
            removed, new_name = make_substitutions(ingredient,
                                                   thai_substitutions_names[ingredient.name],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.adjective in thai_substitutions_adjectives:
            removed, new_name = make_substitutions(ingredient,
                                                   thai_substitutions_adjectives[ingredient.adjective],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.category in thai_substitutions_categories:
            removed, new_name = make_substitutions(ingredient,
                                                   thai_substitutions_categories[ingredient.category],
                                                   added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients


def make_substitutions(ingredient, substitutions, added_ingredients):
    new_name = ''
    if 'substitutions' in substitutions:
        for substitution in substitutions['substitutions']:
            new_name = substitution(ingredient)
    if 'additions' in substitutions:
        for addition in substitutions['additions']:
            new_ingredient = addition(ingredient)
            added_ingredients.append(new_ingredient)
            new_name = new_ingredient.name
    if 'remove' in substitutions:
        return True, new_name
    return False, new_name


if __name__ == '__main__':
    url = 'https://www.allrecipes.com/recipe/173906/cajun-roasted-pork-loin/'
    # url = input('Please provide a recipe URL: ')
    html = urllib.request.urlopen(url)
    recipe = Recipe(url)
    recipe.make_unhealthy()
