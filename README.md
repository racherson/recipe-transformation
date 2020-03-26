# Recipe Transformation


## Setup
Install BeautifulSoup

    pip install beautifulsoup4
    
Install nltk and data
    
    pip install nltk

Install MongoDB (with Homebrew https://brew.sh/)

    brew install mongodb
    mkdir -p ~/data/db (local directory for database contents)

## Using MongoDB
To start a MongoDB process, type the following in the terminal

    mongod --dbpath ~/data/db

Using MondgoDB with Python (see mongo_db.py file)

    pip install pymongo==3.7.1 (use "conda install -n [env_name] pymongo==3.7.1" instead to install in virtual environment)

## Using the App
To use the recipe transformer, run 

    $ python recipe_transform.py
    
Input a URL for an online recipe, such as https://www.allrecipes.com/recipe/173906/cajun-roasted-pork-loin/.

Specify how you would like the recipe transformed. The options are:

    healthy
    unhealthy
    vegetarian
    meatify
    mediterranean
    thai
    
The altered recipe steps will be printed for you.
