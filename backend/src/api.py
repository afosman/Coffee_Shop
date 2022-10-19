import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app)

'''
@TODO uncomment the following line to initialize the datbase
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
!! Running this funciton will add one
'''
db_drop_and_create_all()

'''
Utility functions to help with validation 
'''

def validate_dict(dictionary, keys):
    # To check if the given keys are in the dictionary and the values are not empty
    check_keys = [key in dictionary for key in keys]
        
    # If all keys and values are present
    if all(check_keys) and all(dictionary.values()):
        return True
    
    return False


def validate_recipe(recipe):
    success = False
    # First check if the recipe is a list of dict items 
    if  isinstance(recipe, list) and all( isinstance(recipe_item, dict) for recipe_item in recipe): 
        
            # Check if all recipe items have a `name`, `color` and `part`
            validate_all_recipe = all( 
                            validate_dict(recipe_item, ('name', 'color', 'parts')) for recipe_item in recipe
                        )
        
            success = validate_all_recipe          
               
    return success
            


def validate_create_drink(body):
    error_code = 422
    success = False
    error_body = "The request body must be a json with keys `title` and `recipe`"
     
     
    validate_body = validate_dict(body, ('title', 'recipe'))
    
    if validate_body:

        # After title and recipe is present, Validate the recipe
        
        recipe = body.get('recipe')
        
        success = validate_recipe(recipe)
            
        if not success:
            error_body = "The recipe must be a list containing the dict item(s) for the recipe(s)" 

    return {
            'success': success,
            'error': '' if success else error_code,
            'message': '' if success else error_body
        }



# ROUTES
'''
@TODO implement endpoint
    GET /drinks
        it should be a public endpoint
        it should contain only the drink.short() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks', methods=['GET'])
def drinks():
    drinks = Drink.query.all()
    short_repr = [drink.short() for drink in drinks] 
    
    return jsonify({
        "success": True,
        "drinks": short_repr
    })


'''
@TODO implement endpoint
    GET /drinks-detail
        it should require the 'get:drinks-detail' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''

@app.route('/drinks-detail', methods=['GET'])
@requires_auth('get:drinks-detail')
def drinks_detail(payload):

    drinks = Drink.query.all()
    long_repr = [drink.long() for drink in drinks] 
    
    return jsonify({
        "success": True,
        "drinks": long_repr
    })



'''
@TODO implement endpoint
    POST /drinks
        it should create a new row in the drinks table
        it should require the 'post:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the newly created drink
        or appropriate status code indicating reason for failure
'''

@app.route('/drinks', methods=['POST'])
@requires_auth('post:drinks')
def create_drink(payload):
    
    body = request.get_json()

    results = validate_create_drink(body)
    
    if results['success']:
        # Validation is already successful
        title = body.get('title')
        recipe = body.get('recipe')
        
        new_drink = Drink(title=title, recipe=json.dumps(recipe))
        
        try:
            new_drink.insert()
            
        except:
            abort(500, description={
                'custom_message': f"Internal server error occurred whiles creating the drink."
            })
        
   
    else:
        # When request body validation fails
        abort(results['error'], description={'custom_message': results['message']})
    
    
    return jsonify({
        "success": True,
        "drinks": [new_drink.long()]
    })
    

'''
@TODO implement endpoint
    PATCH /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should update the corresponding row for <id>
        it should require the 'patch:drinks' permission
        it should contain the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the updated drink
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks/<id>', methods=['PATCH'])
@requires_auth('patch:drinks')
def update_drink(payload, id):
    
    body = request.get_json()

    title = body.get('title', None)
    recipe = body.get('recipe', None)
    
    drink = Drink.query.filter(Drink.id == id).one_or_none() 
    
    if drink is None:
        abort(404, description={
                'custom_message': f"Drink with `id` {id} does not exist"
        })
        
    # If recipe is supplied, validate it
    if recipe:

        check_recipe = validate_recipe(recipe)
        
        if not check_recipe:
            abort(422, description={
                "custom_message" : "The recipe must be a list of recipe item(s) dict(s) with keys `name`, `color` and `parts`"
            }) 
        
    # Update only if it is supplied
    drink.title = title if title is not None else drink.title 
    drink.recipe = json.dumps(recipe) if recipe is not None else drink.recipe 
  
    
    try:    
        drink.update()

    except:
        abort(500, description={
                'custom_message': f"Internal server error occurred. Drink with `id` {id} could not be updated"
        })
        
    return jsonify(
            {
                "success": True,
                "drinks": [drink.long()]
            }
    )
    

'''
@TODO implement endpoint
    DELETE /drinks/<id>
        where <id> is the existing model id
        it should respond with a 404 error if <id> is not found
        it should delete the corresponding row for <id>
        it should require the 'delete:drinks' permission
    returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks/<id>', methods=['DELETE'])
@requires_auth('delete:drinks')
def delete_drink(payload, id):
    drink = Drink.query.filter(Drink.id == id).one_or_none() 
        
    if drink is None:
        abort(404, description={
                'custom_message': f"Drink with `id` {id} does not exist"
        })

    try:         
        drink.delete()

    except:
        abort(500, description={
                'custom_message': f"Internal server error occurred. Drink with `id` {id} could not be deleted"
        })
        
    return jsonify({
                "success": True,
                "delete": id
            })


# Error Handling

def customize_error_message(error):
    # to return customized error messages
        try:
            if error.description['custom_message']:
                message = error.description['custom_message']
                return message
        except:
            return None
        

'''
Example error handling for unprocessable entity
'''
@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": customize_error_message(error) or "unprocessable"
    }), 422


'''
@TODO implement error handlers using the @app.errorhandler(error) decorator
    each error handler should return (with approprate messages):
             jsonify({
                    "success": False,
                    "error": 404,
                    "message": "resource not found"
                    }), 404

'''

'''
@TODO implement error handler for 404
    error handler should conform to general task above
'''

@app.errorhandler(404)
def bad_request(error):
    return jsonify({
                    "success": False, 
                    "error": 404, 
                    "message": customize_error_message(error) or "resource not found"
                }), 400
    
    
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
                    "success": False, 
                    "error": 400, 
                    "message": customize_error_message(error) or "bad request"
                }), 400


@app.errorhandler(405)
def not_allowed(error):
    return jsonify({
            "success": False, 
            "error": 405, 
            "message": customize_error_message(error) or "method not allowed"
        }), 405

        
        
@app.errorhandler(500)
def internal_serval_error(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": customize_error_message(error) or "internal server error",    
    })
        
'''
@TODO implement error handler for AuthError
    error handler should conform to general task above
'''
@app.errorhandler(AuthError)
def auth_error(err):
    return jsonify({
        'success': False,
        'error': err.error["code"],
        'message': err.error["description"]
    }), err.status_code





