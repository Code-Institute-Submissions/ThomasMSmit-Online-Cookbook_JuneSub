import os
import math
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for, g)
from flask_pymongo import PyMongo, pymongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from forms import ChangeUsernameForm, ChangePasswordForm
from functools import wraps
if os.path.exists("env.py"):
    import env

app = Flask(__name__)
app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", 'mongodb://localhost')
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

# MongoDb collection variables
# mogelijk weg
users = mongo.db.users
cuisines = mongo.db.cuisines
recipes = mongo.db.recipes
allergens = mongo.db.allergens
ingredients = mongo.db.ingredients

# vervangen met lokale img
placeholder_image = 'http://placehold.jp/48/dedede/adadad/400x400.jpg?text=Image%20Not%20Available'


# Manage session user
@app.before_request
def before_request():
    g.user=None
    if 'user' in session:
        g.user = session['user']

#Home page
@app.route('/')
@app.route("/home")
def home():

    # Generate 4 random recipes from the DB
    featured_recipes = ([recipe for recipe in recipes.aggregate
                        ([{"$sample": {"size": 3}}])])
    
    return render_template('home.html',featured_recipes=featured_recipes, user=g.user,  title='Home')

#Sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Function for registering a new user.
    Also checks if username and/or password
    already exists in the database.
    Redirects to recipelist
    """
    # Checks if user is not already logged in
    if g.user in session:
        flash('You are already registered!')
        return redirect(url_for('login'))

    # Checks if the passwords match
    if request.method == 'POST':
        form = request.form.to_dict()
        if form['password'] == form['password1']:
            registered_user = users.find_one(
                            {"username": form['username']})
    # Checks if username already exists
            if registered_user:
                flash("Username already taken")
                return redirect(url_for('signup'))
    # Hashes the password and puts new user in db
            else:
                hashed_password = generate_password_hash(form['password'])
                users.insert_one(
                    {
                        'username': form['username'],
                        'password': hashed_password
                    }
                )
                user_in_db = users.find_one(
                        {"username": form['username']})
                if user_in_db:
                    session['user'] = user_in_db['username']
                    flash("Account successfully created")
                    return redirect(url_for('signup'))
                else:
                    flash("There was a problem. Please try again.")
                    return redirect(url_for('signup'))
        else:
            flash("Passwords don't match")
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        # Retrieve users from database and check that username exists
        form = request.form.to_dict()
        username_entered = request.form.get('username')
        this_user_in_db = users.find_one({'username': username_entered})
        if not this_user_in_db:
            flash('Username does not exist', 'error')
            return render_template('login.html')

        # once username exists in database confirm password entered
        # and that both fields are populated
        password_entered = request.form.get('password')
        if not username_entered or not password_entered:
            flash('Please enter a valid username and password', 'error')
            return render_template('login.html')

        # check password against this username's user record in database
        if this_user_in_db:
            if check_password_hash(this_user_in_db['password'],
                                   form['password']):
                if form['password'] == form['password1']:
                    # once verified with user record in database,
                    # start a new session and redirect to main recipelist
                    session['user'] = username_entered
                    flash('You have successfully logged in', 'success')
                    return redirect(url_for('home'))
        else:
            # else if password does not match, flash error message
            flash('The password did not match the user profile', 'error')
            return render_template('login.html')

    if g.user:
        return redirect(url_for('login', user=g.user))

    return render_template('login.html')

    # Begin creating new_user dict for possible insertion to database
    # new_user = {}
    # new_user['username'] = request.form.get('username')
    # new_user['email'] = request.form.get('email')
    # Once all required field are populated without error above,
    # insert new user into database and redirect to login page
    # if new_user['username'] and new_user['email'] and new_user['password']:
    # new_user['liked_recipes'] = []
    # db.users.insert_one(new_user)
    # flash('You have successfully signed up, you can now log in', 'success')
    # return redirect(url_for('home'))
    # return render_template('signup.html')


@app.route('/logout')
def logout():
    # remove the user and user_id from the session if it's there
    session.pop('user', None)
    flash('You have successfully logged out', 'success')
    return redirect(url_for('login'))


@app.route('/recipelist')
def recipelist():
    cuisines = mongo.db.cuisines
    recipes = mongo.db.recipes
    cuisines = list(cuisines.find().sort('cuisine_name', 1))
    recipes = list(recipes.find())

    for arg in request.args:
        if 'recipe_search' in arg:
            new_recipe_list = []
            query = request.args['recipe_search']
            for recipe in recipes:
                if recipe['recipe_name'].lower().find(query.lower()) != -1:
                    new_recipe_list.append(recipe)
            return render_template('recipelist.html', recipes=new_recipe_list,
                                   cuisines=cuisines, user=g.user)

        elif 'cuisine_select' in arg:
            new_recipe_list = []
            query = request.args['cuisine_select']
            for recipe in recipes:
                if recipe['cuisine'] == query:
                    new_recipe_list.append(recipe)
            return render_template('recipelist.html', recipes=new_recipe_list,
                                   cuisines=cuisines, user=g.user)

        elif 'sort' in arg:
            if request.args['sort'] == 'votes':
                new_recipe_list = list(mongo.db.recipes.find().sort('upvotes', -1))
                return render_template('recipelist.html',
                                       recipes=new_recipe_list,
                                       cuisines=cuisines, user=g.user)
            elif request.args['sort'] == 'asc':
                new_recipe_list = list(mongo.db.recipes.find().sort('recipe_name', 1))
                return render_template('recipelist.html',
                                       recipes=new_recipe_list,
                                       cuisines=cuisines,
                                       user=g.user)
            elif request.args['sort'] == 'dsc':
                new_recipe_list = list(mongo.db.recipes.find().sort('recipe_name', -1))
                return render_template('recipelist.html',
                                       recipes=new_recipe_list,
                                       cuisines=cuisines, user=g.user)

    return render_template('recipelist.html', recipes=recipes,
                           cuisines=cuisines, user=g.user)


@app.route('/recipe/<recipe_id>/')
def recipe(recipe_id):
    this_recipe = recipes.find_one({'_id': ObjectId(recipe_id)})
    recipe_id = str(this_recipe['_id'])
    allergens = list(mongo.db.allergens.find())
    return render_template('recipe.html', recipe=this_recipe,
                           allergens=allergens, user=g.user,
                           recipe_id=recipe_id)


@app.route('/add_like/<recipe_id>/<user>/', methods=['POST'])
def add_like(recipe_id, user):

    # update liked_by list in recipe
    this_recipe = recipes.find_one({'_id': ObjectId(recipe_id)})
    liked_by = list(this_recipe['liked_by'])
    if user not in liked_by:
        liked_by.append(user)
    this_recipe['liked_by'] = liked_by
    this_recipe['upvotes'] = len(liked_by)
    recipes.update_one({'_id': ObjectId(recipe_id)}, {'$set': this_recipe})

    # update liked_recipes list in user
    this_user = users.find_one({'username': user})
    liked_recipes = list(this_user['liked_recipes'])
    if recipe_id not in liked_recipes:
        liked_recipes.append(recipe_id)
    this_user['liked_recipes'] = liked_recipes
    users.update_one({'username': user}, {'$set': this_user})

    return "Recipe Liked by User"


@app.route('/remove_like/<recipe_id>/<user>/', methods=['POST'])
def remove_like(recipe_id, user):

    # update liked_by list in recipe
    this_recipe = recipes.find_one({'_id': ObjectId(recipe_id)})
    liked_by = list(this_recipe['liked_by'])
    if user in liked_by:
        liked_by.remove(user)
    this_recipe['liked_by'] = liked_by
    this_recipe['upvotes'] = len(liked_by)
    recipes.update_one({'_id': ObjectId(recipe_id)}, {'$set': this_recipe})

    # update liked_recipes list in user
    this_user = users.find_one({'username': user})
    liked_recipes = list(this_user['liked_recipes'])
    if recipe_id in liked_recipes:
        liked_recipes.remove(recipe_id)
    this_user['liked_recipes'] = liked_recipes
    users.update_one({'username': user}, {'$set': this_user})

    return "Recipe Un-Liked by User"


@app.route('/add_recipe')
def add_recipe():
    allergens = mongo.db.allergens
    ingredients = mongo.db.ingredients
    cuisines = mongo.db.cuisines
    cuisines = list(cuisines.find().sort('cuisine_name', 1))
    ingredients = list(ingredients.find().sort('ingredient_name', 1))
    allergens = list(allergens.find())
    return render_template('add_recipe.html', cuisines=cuisines,
                           ingredients=ingredients, allergens=allergens,
                           user=g.user)


@app.route('/edit_recipe/<recipe_id>/')
def edit_recipe(recipe_id):
    cuisines = mongo.db.cuisines
    allergens = mongo.db.allergens
    ingredients = mongo.db.ingredients
    cuisines = list(cuisines.find().sort('cuisine_name', 1))
    ingredients = list(ingredients.find().sort('ingredient_name', 1))
    allergens = list(allergens.find())
    this_recipe = recipes.find_one({'_id': ObjectId(recipe_id)})
    return render_template('edit_recipe.html', cuisines=cuisines,
                           ingredients=ingredients, allergens=allergens,
                           recipe=this_recipe, user=g.user )


@app.route('/update_recipe/<recipe_id>', methods=["POST"])
def update_recipe(recipe_id):

    # organise method steps from form and build
    # new ordered array containing them
    step_keys = []
    method_steps = []
    for stepkey in request.form.to_dict():
        if 'step' in stepkey:
            step_keys.append(stepkey)
    for i in range(1, len(step_keys) + 1):
        method_steps.append(request.form.get('step-' + str(i)))

    # organise ingredients from form and build new 2D containing
    # qty-ingredient pairs
    ingredients_arr = []
    qty_arr = []
    ing_arr = []
    for ing_key in request.form.to_dict():
        if 'ingredient-qty-' in ing_key:
            qty_arr.append(ing_key)
        if 'ingredient-name-' in ing_key:
            ing_arr.append(ing_key)
    for i in range(1, len(qty_arr) + 1):
        qty = request.form.get('ingredient-qty-' + str(i))
        ing = request.form.get('ingredient-name-' + str(i))
        ingredients_arr.append([qty, ing])

    # find selected allergens and form new array containing them
    allergens = mongo.db.allergens.find()
    allergen_arr = []
    for allergen in list(allergens):
        for key in request.form.to_dict():
            if key == allergen['allergen_name']:
                allergen_arr.append(key)

    # create new document that will be used as the update
    # dict to update database
    updated_recipe = {}
    updated_recipe['recipe_name'] = request.form.get('recipe_name')
    updated_recipe['ingredients'] = ingredients_arr
    updated_recipe['method'] = method_steps
    updated_recipe['allergens'] = allergen_arr
    updated_recipe['cuisine'] = request.form.get('cuisine')
    if request.form.get('image_url') == "":
        updated_recipe['image_url'] = placeholder_image
    else:
        updated_recipe['image_url'] = request.form.get('image_url')
    recipes.update_one({'_id': ObjectId(recipe_id)}, {'$set': updated_recipe})

    return redirect(url_for('recipelist'))


@app.route('/delete_recipe/<recipe_id>')
def delete_recipe(recipe_id):
    recipes.delete_one({'_id': ObjectId(recipe_id)})
    flash('Recipe successfully deleted', 'success')
    return redirect(url_for('recipelist'))


@app.route('/insert_recipe', methods=['POST'])
def insert_recipe():

    # organise method steps from form and build
    # new ordered array containing them
    step_keys = []
    method_steps = []
    for stepkey in request.form.to_dict():
        step_keys.append(stepkey)
    for i in range(1, len(step_keys) + 1):
        method_steps.append(request.form.get('step-' + str(i)))

    # organise ingredients from form and build
    # new 2D containing qty-ingredient pairs
    ingredients_arr = []
    qty_arr = []
    ing_arr = []
    for ing_key in request.form.to_dict():
        if 'ingredient-qty-' in ing_key:
            qty_arr.append(ing_key)
        if 'ingredient-name-' in ing_key:
            ing_arr.append(ing_key)
    for i in range(1, len(qty_arr) + 1):
        qty = request.form.get('ingredient-qty-' + str(i))
        ing = request.form.get('ingredient-name-' + str(i))
        ingredients_arr.append([qty, ing])

    # find selected allergens and form new array containing them
    allergens = mongo.db.allergens.find()
    # allergens = allergens.find()
    allergen_arr = []
    for allergens in list(allergens):
        for key in request.form.to_dict():
                allergen_arr.append(key)

    # create new database document and insert it to database
    new_recipe = {}
    new_recipe['recipe_name'] = request.form.get('recipe_name')
    new_recipe['ingredients'] = ingredients_arr
    new_recipe['method'] = method_steps
    new_recipe['allergens'] = allergen_arr
    new_recipe['liked_by'] = []
    new_recipe['author'] = session["user"]
    new_recipe['cuisine'] = request.form.get('cuisine')
    if request.form.get('image_url') == "":
        new_recipe['image_url'] = placeholder_image
    else:
        new_recipe['image_url'] = request.form.get('image_url')
    recipes.insert_one(new_recipe)
    flash('Recipe successfully created', 'success')
    return redirect(url_for('recipelist'))



# My recipes
@app.route('/my_recipes/<user>')
def my_recipes(user):
    
    my_username = mongo.db.users.find_one({'username': session['user']})['username']
    # finds all user's recipes by author 
    my_recipes = mongo.db.recipes.find({'author': user})
    # get total number of recipes created by the user
    number_of_my_rec = my_recipes.count()

    limit_per_page = 6
    current_page = int(request.args.get('current_page', 1))
    pages = range(1, int(math.ceil(number_of_my_rec / limit_per_page)) + 1)
    recipes = my_recipes.sort('user', pymongo.ASCENDING).skip(
        (current_page - 1)*limit_per_page).limit(limit_per_page)
    
    
    return render_template("my_recipes.html", my_recipes=my_recipes,
                           user=my_username, recipes=recipes, pages=pages,
                           number_of_my_rec=number_of_my_rec, current_page=current_page,
                           title='My Recipes')


# Account Settings
@app.route("/account_settings/<user>")
def account_settings(user):

    user = users.find_one({'username':
                                    session['user']})['username']
    return render_template('account_settings.html',
                           user=g.user, title='Account Settings')

# Change username
@app.route("/change_username/<user>", methods=['GET', 'POST'])
def change_username(user):
    
    users = mongo.db.users
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        # checks if the new username is unique
        registered_user = users.find_one({'username':
                                         request.form['new_username']})
        if registered_user:
            flash('Sorry, username is already taken. Try another one')
            return redirect(url_for('change_username',
                                    user=session["user"]))
        else:
            users.update_one(
                {"username": user},
                {"$set": {"username": request.form["new_username"]}})
        # clear the session and redirect to login page
        flash("Your username was updated successfully.\
                    Please, login with your new username")
        session.pop("username",  None)
        return redirect(url_for("logout"))

    return render_template('change_username.html',
                           user=session["user"],
                           form=form, title='Change Username')

# Change password
@app.route("/change_password/<user>", methods=['GET', 'POST'])
def change_password(user):
    
    users = mongo.db.users
    form = ChangePasswordForm()
    username = users.find_one({'username': session['user']})['username']
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get("confirm_new_password")
    if form.validate_on_submit():
        # checks if current password matches existing password in database
        if check_password_hash(users.find_one({'username': username})
                               ['password'], old_password):
            # checks if new passwords match
            if new_password == confirm_password:
                # update the password and redirect to the settings page
                users.update_one({'username': username},
                                 {'$set': {'password': generate_password_hash
                                           (request.form['new_password'])}})
                flash("Success! Your password was updated.")
                return redirect(url_for('logout', user=g.user))
            else:
                flash("New passwords do not match! Please try again")
                return redirect(url_for("change_password",
                                        user=session["user"]))
        else:
            flash('Incorrect original password! Please try again')
            return redirect(url_for('change_password',
                            user=session["user"]))
    return render_template('change_password.html', user=g.user,
                           form=form, title='Change Password')

# Delete Account
@app.route("/delete_account/<user>", methods=['GET', 'POST'])
def delete_account(user):
    
    username = users.find_one({'username': session['user']})['username']
    user = users.find_one({"username": username})
    # checks if password matches existing password in database
    if check_password_hash(user["password"],
                           request.form.get("confirm_password_to_delete")):
        # Removes all user's recipes from the Database
        all_user_recipes = user.get("user_recipes")
        for recipe in all_user_recipes:
            recipes.remove({"_id": recipe})
        # remove user from database,clear session and redirect to the home page
        flash("Your account has been deleted.")
        session.pop("username", None)
        users.remove({"_id": user.get("_id")})
        return redirect(url_for("home"))
    else:
        flash("Password is incorrect! Please try again")
        return redirect(url_for("account_settings", user=g.user))





















# Error Handling
# @app.errorhandler(404)
# def page_not_found(error):
#     return render_template('404.html'), 404

# @app.errorhandler(500)
# def something_wrong(error):
#     return render_template('500.html'), 500


# run application
if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=False)