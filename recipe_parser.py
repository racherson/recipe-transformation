import functools
import pymongo
import urllib.request
from bs4 import BeautifulSoup
import nltk
from pprint import pprint
import collections
nltk.download('punkt')

# global variables (NEED TO ADD MORE)
METHODS = ['saute', 'broil', 'boil', 'poach', 'bake', 'grill', 'fry', 'bake', 'heat', 'mix', 'chop', 'grate', 'stir', 'shake', 'mince', 'crush', 'squeeze', 'dice']
TOOLS = ['pan', 'grater', 'whisk', 'pot', 'spatula', 'tong', 'oven', 'knife']
stopwords = nltk.corpus.stopwords.words('english')
custom_stopwords = [",",".","!","?","(",")"]
stopwords.extend(custom_stopwords)

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
        print ('Name: ', self.name)

        # get ingredients
        ingredients = self.soup.find_all("span", class_="recipe-ingred_txt added")
        self.ingredients = [add_ingredient(ingredient.contents[0]) for ingredient in ingredients]
        self.substitute_ingredients = substitute_ingredients(self.ingredients)
        print ('Ingredients: ')
        for ingredient in self.substitute_ingredients:
            print(ingredient)

        # get steps (list of steps where each item can be multiple sentences)
        self.steps = self.get_steps()
        print ('Steps: ', self.steps)

        # get tools
        self.tools, methods_counter = self.get_tools_methods()
        self.tools = list(self.tools)
        print ('Tools: ', self.tools)

        # get primary method (most commonly mentioned method) and other methods if exist
        self.primary_method = methods_counter.most_common(1)[0][0]
        del methods_counter[self.primary_method]
        self.other_methods = list(methods_counter)
        print ('Primary method: ', self.primary_method)
        print ('Other methods: ', self.other_methods)

    def get_steps(self):
        # get steps from html
        steps = self.soup.find("ol", {"class":"list-numbers recipe-directions__list"})
        substeps = steps("li")
        final_steps = []
        for s in substeps:
            curr_step = s.find("span").string
            final_steps.append(curr_step.strip())

        return final_steps

    def get_tools_methods(self):
        tools = set() # unique set
        methods_counter = collections.Counter() # frequency mapping
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

    def make_json(self):
        recipe = {'ingredients': self.ingredients, 'tools': self.tools, 'primary_method': self.primary_method, 'other_methods': self.other_methods, 'steps': self.steps}
        res = json.dumps(recipe)
        pprint (res)
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


def change_adjective(adjective, ingredient):
    ingredient.adjective = adjective


def change_category(category, ingredient):
    ingredient.category = category


def change_amount(delta, ingredient):
    ingredient.amount *= delta


def change_unit(unit, ingredient):
    ingredient.unit = unit


# healthy substitutions dictionaries

healthy_substitutions_names = {
    "shortening": {"substitutions": [functools.partial(change_amount, 0.5)],
                   "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)]},
    "oil": {"substitutions": [functools.partial(change_amount, 0.5)],
            "additions": [functools.partial(ingredient_delta, "applesauce", "unsweetened", "sauce", 1)]},
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
                                    functools.partial(change_adjective, "cococa")]},
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


# vegetarian substitutions dictionaries

vegetarian_substitutions_names = {}
vegetarian_substitutions_adjectives = {}
vegetarian_substitutions_categories = {}
vegetarian_substitutions_exceptions = {}


# cuisine substitutions dictionaries

cuisine_substitutions_names = {}
cuisine_substitutions_adjectives = {}
cuisine_substitutions_categories = {}
cuisine_substitutions_exceptions = {}

# helper functions

def make_substitutions(ingredient, substitutions, added_ingredients):
    if "substitutions" in substitutions:
        for substitution in substitutions["substitutions"]:
            substitution(ingredient)
    if "additions" in substitutions:
        for addition in substitutions["additions"]:
            added_ingredients.append(addition(ingredient))
    if "remove" in substitutions:
        return True
    return False


def substitute_ingredients(ingredients):
    global healthy_substitutions_names
    global healthy_substitutions_adjectives
    global healthy_substitutions_categories
    global healthy_substitutions_exceptions
    added_ingredients = []
    removed_ingredients = []
    # loop through ingredients and make substitutions
    for ingredient in ingredients:
        full_name = ingredient.name
        if ingredient.adjective:
            full_name = ingredient.adjective + " " + full_name
        if full_name in healthy_substitutions_exceptions:
            make_substitutions(ingredient, healthy_substitutions_exceptions[full_name], added_ingredients)
            continue
        if ingredient.name in healthy_substitutions_names:
            removed = make_substitutions(ingredient, healthy_substitutions_names[ingredient.name], added_ingredients)
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.adjective in healthy_substitutions_adjectives:
            removed = make_substitutions(ingredient, healthy_substitutions_adjectives[ingredient.adjective], added_ingredients)
            if removed:
                removed_ingredients.append(ingredient)
                continue
        if ingredient.category in healthy_substitutions_categories:
            removed = make_substitutions(ingredient, healthy_substitutions_categories[ingredient.category], added_ingredients)
            if removed:
                removed_ingredients.append(ingredient)
                continue
    for ingredient in removed_ingredients:
        ingredients.remove(ingredient)
    ingredients += added_ingredients

    return ingredients

def add_ingredient(ingredient_text):
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
    #transform_recipe(html)
    Recipe(url)
