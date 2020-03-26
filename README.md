# Recipe Transformation
EECS 339 Project 2

## Setup
Install BeautifulSoup

    pip install beautifulsoup4
    
Install nltk and data
    
    pip install nltk

Install MongoDB
1. If not already installed, install Homebrew: https://brew.sh/
2. In terminal: brew install mongodb
3. In terminal: mkdir -p ~/data/db (local directory for database contents)

To start a MongoDB process, type the following in the terminal: mongod --dbpath ~/data/db

* Using MondgoDB with Python
1. In terminal: pip install pymongo==3.7.1 (use "conda install -n [env_name] pymongo==3.7.1" instead to install in virtual environment)
2. See mongo_db.py file

## Use
To use the recipe transformer, run 

    $ python recipe_transform.py
    
Input a URL for an online recipe, such as 'https://www.allrecipes.com/recipe/173906/cajun-roasted-pork-loin/'.
Specify how you would like the recipe transformed: Type "healthy", "unhealthy", "vegetarian", "meatify", "mediterranean", or "thai" (without quotes).
The altered recipe steps will be printed for you.
