import functools
import pymongo
import urllib.request
from bs4 import BeautifulSoup
import nltk
from pprint import pprint
import collections
nltk.download('punkt')

# global variables (NEED TO ADD MORE)
METHODS = ['add', 'use', 'blend', 'cut', 'strain', 'roast', 'slice', 'flip', 'baste', 'simmer', 'grate', 'drain', 'saute', 'broil', 'boil', 'poach', 'bake', 'grill', 'fry', 'bake', 'heat', 'mix', 'chop', 'grate', 'stir', 'shake', 'mince', 'crush', 'squeeze', 'dice', 'rub', 'cook']
TOOLS = ['pan', 'grater', 'whisk', 'pot', 'spatula', 'tong', 'oven', 'knife']
stopwords = nltk.corpus.stopwords.words('english')
custom_stopwords = [",", ".", "!", "?", "(", ")"]
stopwords.extend(custom_stopwords)
ingredient_switches = {}


ingredient_categories = {
    "healthy_fats": ['olive oil', 'sunflower oil', 'soybean oil', 'corn oil',  'sesame oil',  'peanut oil'],
    "unhealthy_fats": ['butter', 'lard', 'shortening', 'canola oil', 'margarine',  'coconut oil',  'tallow',  'cream', 'milk fat',  'palm oil',  'palm kemel oil',  'chicken fat',  'hydrogenated oils'],
    "healthy_protein": [ 'peas',  'beans', 'eggs', 'crab', 'fish','chicken', 'tofu', 'liver', 'turkey'],
    "unhealthy_protein": ['ground beef', 'beef', 'pork', 'lamb'],
    "healthy_dairy": ['fat free milk', 'low fat milk', 'yogurt',  'low fat cheese'],
    "unhealthy_dairy": ['reduced-fat milk', 'cream cheese', 'whole milk', 'butter', 'cheese', 'whipped cream', 'sour cream'],
    "healthy_salts": ['low sodium soy sauce', 'sea salt', 'kosher salt'],
    "unhealthy_salts": ['soy sauce', 'table salt', 'salt'],
    "healthy_grains": ['oat cereal', 'wild rice', 'oatmeal', 'whole rye', 'buckwheat', 'rolled oats', 'quinoa','bulgur', 'millet', 'brown rice', 'whole wheat pasta'],
    "unhealthy_grains": ['macaroni', 'noodles', 'spaghetti', 'white rice', 'white bread', 'regular white pasta'],
    "healthy_sugars": ['real fruit jam', 'fruit juice concentrates', 'monk fruit extract', 'cane sugar', 'molasses', 'brown rice syrup' 'stevia', 'honey', 'maple syrup', 'agave syrup', 'coconut sugar', 'date sugar', 'sugar alcohols', 'brown sugar'],
    "unhealthy_sugars": ['aspartame', 'acesulfame K', 'sucralose', 'white sugar', 'corn syrup', 'chocolate syrup']
}
# categorized foods found at https://github.com/olivergoodman/food-recipes/blob/master/transforms.py

# recipe class definition
class Recipe:
    def __init__(self, url):
        # take url and load recipe from web
        self.url = url
        html = urllib.request.urlopen(url)
        self.soup = BeautifulSoup(html, 'html.parser')

        # get name of recipe
        name = self.soup.find("h1", {"id": "recipe-main-content"})
        self.name = name.string
        print('Name: ', self.name)

        # get steps (list of steps where each item can be multiple sentences)
        self.steps = self.get_steps()
        print('Steps: ', self.steps)

        # get tools
        self.tools, methods_counter = self.get_tools_methods()
        self.tools = list(self.tools)
        print('Tools: ', self.tools)

        # get primary method (most commonly mentioned method) and other methods if exist
        self.primary_method = methods_counter.most_common(1)[0][0]
        del methods_counter[self.primary_method]
        self.other_methods = list(methods_counter)
        if "bake" in self.other_methods:
            self.bake = True
        else:
            self.bake = False
        print('Baking?: ', self.bake)
        print('Primary method: ', self.primary_method)
        print('Other methods: ', self.other_methods)

        # get ingredients
        ingredients = self.soup.find_all("span", class_="recipe-ingred_txt added")
        self.ingredients = [add_ingredient(ingredient.contents[0]) for ingredient in ingredients]
        self.substitute_ingredients = substitute_ingredients(self.ingredients, self.bake)
        print('Ingredients: ')
        for ingredient in self.substitute_ingredients:
            print(ingredient)
        # TODO: merge ingredients if they are in same step
        # TODO: deal with salt...

        self.steps = self.alter_steps()
        print('Changed steps:', self.steps)

    def get_steps(self):
        # get steps from html
        steps = self.soup.find("ol", {"class": "list-numbers recipe-directions__list"})
        substeps = steps("li")
        final_steps = []
        for s in substeps:
            curr_step = s.find("span").string
            final_steps.append(curr_step.strip())

        return final_steps

    def get_tools_methods(self):
        tools = set()  # unique set
        methods_counter = collections.Counter()  # frequency mapping
        for step in self.steps:
            tokens = nltk.word_tokenize(step)
            tokens = [token.lower() for token in tokens if not token in stopwords]
            bigrams = nltk.bigrams(tokens)
            # check tokens in unigrams
            for token in tokens:
                if token in TOOLS:
                    tools.add(token)
                if token in METHODS:
                    methods_counter[token] += 1

            # check tokens in bigrams
            for token in bigrams:
                if token in TOOLS:
                    tools.add(token)
                if token in METHODS:
                    methods_counter[token] += 1

        return tools, methods_counter

    def alter_steps(self):
        global ingredient_switches
        punctuation = [",", ".", "!", "?", ")"]
        new_steps = []
        old_steps = self.steps[:]
        for step in old_steps:
            tokens = nltk.word_tokenize(step)
            new_curr_step = ""
            for token in tokens:
                found = False
                for ingredient in ingredient_switches:
                    if token.lower() == ingredient:
                        new_curr_step += ingredient_switches[ingredient] + " "
                        found = True
                        break
                if not found:
                    if token in punctuation:
                        new_curr_step = new_curr_step[:-1]
                        new_curr_step += token + " "
                    elif token == "(":
                        new_curr_step += token
                    else:
                        new_curr_step += token + " "
            new_curr_step = new_curr_step[:-1]
            new_steps.append(new_curr_step)

        return new_steps

    def make_json(self):
        recipe = {'ingredients': self.ingredients, 'tools': self.tools, 'primary_method': self.primary_method, 'other_methods': self.other_methods, 'steps': self.steps}
        res = json.dumps(recipe)
        pprint(res)
        return res


# ingredient class definition
class Ingredient:
    def __init__(self, name, adjective, category, amount, unit):
        self.name = name
        self.adjective = adjective
        self.category = category
        self.amount = amount
        self.unit = unit

    def __str__(self):
        output = ""
        if self.amount:
            output += str(self.amount) + " "
        if self.unit:
            output += self.unit + " "
        if self.adjective:
            output += self.adjective + " "
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


# healthy substitutions dictionaries

healthy_substitutions_names = {
    "shortening": {"substitutions": [functools.partial(change_amount, 0.5)],
                   "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)],
                   "remove": None},
    "oil": {"substitutions": [functools.partial(change_adjective, "olive")]},
    "butter": {"substitutions": [functools.partial(change_amount, 0.5)],
               "additions": [functools.partial(ingredient_delta, "oil", "olive", "oil", 1)],
               "remove": None},
    "sugar": {"substitutions": [functools.partial(change_name, "stevia")]},
    "salt": {"substitutions": [functools.partial(change_adjective, "himalayan")]},
    "pasta": {"substitutions": [functools.partial(change_adjective, "whole-wheat")]},
    "milk": {"substitutions": [functools.partial(change_adjective, "almond")]},
    "cheese": {"substitutions": [functools.partial(change_amount, 0.5)]},
    "jelly": {"additions": [ingredient_base],
              "remove": None},
    "egg": {"substitutions": [functools.partial(change_adjective, "substitute"),
                              functools.partial(change_amount, 0.25),
                              functools.partial(change_unit, "cup")]},
    "rice": {"substitutions": [functools.partial(change_name, "quinoa")]},
    "flour": {"substitutions": [functools.partial(change_adjective, "whole-wheat")]},
    "chocolate": {"substitutions": [functools.partial(change_name, "nibs"),
                                    functools.partial(change_adjective, "cocoa")]},
}
healthy_substitutions_adjectives = {
    "iceberg": {"substitutions": [functools.partial(change_adjective, "romaine")]},
    "peanut": {"substitutions": [functools.partial(change_adjective, "almond")]},
}
healthy_substitutions_categories = {
    "topping": {"remove": None},
    "condiment": {"remove": None},
    "vegetable": {"substitutions": [functools.partial(change_amount, 2)]},
}
healthy_substitutions_exceptions = {
    "peanut butter": {"substitutions": [functools.partial(change_adjective, "almond")]},
    "sour cream": {"substitutions": [functools.partial(change_name, "yogurt"),
                                     functools.partial(change_adjective, "greek")]},
}

# for baking!
baking_healthy_substitutions_names = {
    "shortening": {"substitutions": [functools.partial(change_amount, 0.5)],
                   "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)],
                   "remove": None},
    "oil": {"substitutions": [functools.partial(change_amount, 0.5)],
            "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)],
            "remove": None},
    "butter": {"substitutions": [functools.partial(change_amount, 0.5)],
               "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)],
               "remove": None},
    "sugar": {"substitutions": [functools.partial(change_name, "stevia")]},
    "salt": {"substitutions": [functools.partial(change_adjective, "himalayan")]},
    "milk": {"substitutions": [functools.partial(change_adjective, "almond")]},
    "cheese": {"substitutions": [functools.partial(change_amount, 0.5)]},
    "jelly": {"additions": [ingredient_base],
              "remove": None},
    "egg": {"substitutions": [functools.partial(change_adjective, "substitute"),
                              functools.partial(change_amount, 0.25),
                              functools.partial(change_unit, "cup")]},
    "flour": {"substitutions": [functools.partial(change_adjective, "whole-wheat")]},
    "chocolate": {"substitutions": [functools.partial(change_name, "nibs"),
                                    functools.partial(change_adjective, "cocoa")]},
}
baking_healthy_substitutions_adjectives = {
    "peanut": {"substitutions": [functools.partial(change_adjective, "almond")]}
}
baking_healthy_substitutions_categories = {
    "topping": {"remove": None}
}
baking_healthy_substitutions_exceptions = {
    "peanut butter": {"substitutions": [functools.partial(change_adjective, "almond")]}
}


# vegetarian substitutions dictionaries

vegetarian_substitutions_names = {
    "chicken": {"substitutions": [functools.partial(change_name, "eggplant")]},
    "pork": {"substitutions": [functools.partial(change_name, "tofu")]},
    "beef": {"substitutions": [functools.partial(change_name, "lentils")]},
    "steak": {"substitutions": [functools.partial(change_name, "mushroom"),
                                functools.partial(change_adjective, "portobello")]},
    "bacon": {"substitutions": [functools.partial(change_adjective, "seitan")]},
    "fish": {"substitutions": [functools.partial(change_name, "tofu")]}
}
vegetarian_substitutions_adjectives = {
    "chicken": {"substitutions": [functools.partial(change_adjective, "vegetable")]},
    "pork": {"substitutions": [functools.partial(change_adjective, "vegetable")]},
    "beef": {"substitutions": [functools.partial(change_adjective, "vegetable")]},
}
vegetarian_substitutions_categories = {}
vegetarian_substitutions_exceptions = {}


# cuisine (thai) substitutions dictionaries

cuisine_substitutions_names = {
    "salt": {"substitutions": [functools.partial(change_name, "fish sauce"),
                               functools.partial(change_adjective, "thai"),
                               functools.partial(change_amount, 1),
                               functools.partial(change_unit, "tablespoon")]},
    "broccoli": {"substitutions": [functools.partial(change_adjective, "chinese")]},
    "pasta": {"substitutions": [functools.partial(change_adjective, "rice"),
                                functools.partial(change_name, "noodles")]},
    "noodles": {"substitutions": [functools.partial(change_adjective, "rice")]},
    "milk": {"substitutions": [functools.partial(change_adjective, "coconut")]},
    "onions": {"substitutions": [functools.partial(change_name, "shallots")]},
    "basil": {"substitutions": [functools.partial(change_adjective, "thai")]},
}
cuisine_substitutions_adjectives = {
    "whole-wheat": {"substitutions": [functools.partial(change_adjective, "rice")]}
}
cuisine_substitutions_categories = {
    "sauce": {"substitutions": [functools.partial(change_adjective, "thai"),
                                functools.partial(change_name, "curry paste")]}
}
cuisine_substitutions_exceptions = {}

# helper functions


def make_substitutions(ingredient, substitutions, added_ingredients):
    new_name = ""
    if "substitutions" in substitutions:
        for substitution in substitutions["substitutions"]:
            new_name = substitution(ingredient)
    if "additions" in substitutions:
        for addition in substitutions["additions"]:
            new_ingredient = addition(ingredient)
            added_ingredients.append(new_ingredient)
            new_name = new_ingredient.name
    if "remove" in substitutions:
        return True, new_name
    return False, new_name


def make_vegetarian(ingredients):
    global vegetarian_substitutions_names
    global vegetarian_substitutions_adjectives
    global vegetarian_substitutions_categories
    global vegetarian_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    global ingredient_switches
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + " " + full_name
        if full_name in vegetarian_substitutions_exceptions:
            removed, new_name = make_substitutions(ingredient, vegetarian_substitutions_exceptions[full_name], added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            continue
        if ingredient.name in vegetarian_substitutions_names:
            removed, new_name = make_substitutions(ingredient, vegetarian_substitutions_names[ingredient.name], added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.adjective in vegetarian_substitutions_adjectives:
            removed, new_name = make_substitutions(ingredient, vegetarian_substitutions_adjectives[ingredient.adjective], added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.category in vegetarian_substitutions_categories:
            removed, new_name = make_substitutions(ingredient, vegetarian_substitutions_categories[ingredient.category], added_ingredients)
            ingredient_switches[ingredient.name] = new_name
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients

    return ingredients


def substitute_ingredients(ingredients, bake):
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
    global ingredient_switches
    # loop through ingredients and make substitutions
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + " " + full_name
        if bake is True:
            if full_name in baking_healthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient, baking_healthy_substitutions_exceptions[full_name], added_ingredients)
                ingredient_switches[ingredient.name] = new_name  # NEW THING
                continue
            if ingredient.name in baking_healthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient, baking_healthy_substitutions_names[ingredient.name], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in baking_healthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient, baking_healthy_substitutions_adjectives[ingredient.adjective], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in baking_healthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient, baking_healthy_substitutions_categories[ingredient.category], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
        else:
            if full_name in healthy_substitutions_exceptions:
                removed, new_name = make_substitutions(ingredient, healthy_substitutions_exceptions[full_name], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                continue
            if ingredient.name in healthy_substitutions_names:
                removed, new_name = make_substitutions(ingredient, healthy_substitutions_names[ingredient.name], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.adjective in healthy_substitutions_adjectives:
                removed, new_name = make_substitutions(ingredient, healthy_substitutions_adjectives[ingredient.adjective], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
            if ingredient.category in healthy_substitutions_categories:
                removed, new_name = make_substitutions(ingredient, healthy_substitutions_categories[ingredient.category], added_ingredients)
                ingredient_switches[ingredient.name] = new_name
                if removed:
                    removed_ingredients.append(ingredient)
                    continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients

    return ingredients


def add_ingredient(ingredient_text):  # TODO: Set Category
    adjective = None
    category = None
    amount = None
    unit = None
    ingredient_parts = ingredient_text.split(', ')
    ingredient = ingredient_parts[0]
    if len(ingredient_parts) > 1:
        ingredient_style = ingredient_parts[1]
    ingredient_words = ingredient.split(' ')
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
            adjective += " " + word
    return Ingredient(name, adjective, category, amount, unit)


# def transform_recipe(html):
#     soup = BeautifulSoup(html, 'html.parser')
#     ingredients = soup.find_all("span", class_="recipe-ingred_txt added")
#     ingredients = [add_ingredient(ingredient.contents[0]) for ingredient in ingredients]
#     substitute_ingredients(ingredients)
#     for ingredient in ingredients:
#         print(ingredient)
#     return

if __name__ == "__main__":
    url = "https://www.allrecipes.com/recipe/173906/cajun-roasted-pork-loin/"
    # url = input("Please provide a recipe URL: ")
    html = urllib.request.urlopen(url)
    # transform_recipe(html)
    Recipe(url)
