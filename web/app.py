from flask import Flask,jsonify,request
from flask_restful import Api,Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.bankApi
users = db["users"]

def user_exists(username):
    return users.find({
        "username":username
    }).count()!=0

def verify_pw(username,password):
    if not user_exists(username):
        return False

    hashed_pw = users.find({
        "username":username
    })[0]["password"]

    return bcrypt.hashpw(password.encode('utf8'),hashed_pw)==hashed_pw

def cash_with_user(username):
    cash = users.find({
        "username":username
    })[0]["own"]

    return cash

def debt_with_user(username):
    debt = users.find({
        "username":username
    })[0]["debt"]

    return debt

def generate_return_dictionary(status,msg):
    ret_json = {
        "status":status,
        "msg":msg
    }
    return ret_json

# ErrorDictionary, True/False
def verify_credentials(username,password):
    if not user_exists(username):
        return generate_return_dictionary(301,"Invalid username"),True
    
    correct_pw = verify_pw(username, password)

    if not correct_pw:
        return generate_return_dictionary(302,"Incorrect password"),True

    return None,False

def update_account(username,balance):
    users.update({
        "username":username
    },{
        "$set":{
            "own":balance
        }
    })

def update_debt(username,balance):
    users.update({
        "username":username
    },{
        "$set":{
            "debt":balance
        }
    })

class Add(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money    = posted_data["amount"]

        ret_json, error = verify_credentials(username,password)

        if error:
            return jsonify(ret_json)

        if money<=0:
            return jsonify(generate_return_dictionary(304,"The money amount entered must be > 0"))

        cash = cash_with_user(username)
        money-=1
        bank_cash=cash_with_user("BANK")
        update_account("BANK",bank_cash+1)
        update_account(username,cash+money)

        return jsonify(generate_return_dictionary(200,"Amount added successfully to account."))

class Register(Resource):
    def post(self):
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]

        if user_exists(username):
            ret_json = {
                "status":"301",
                "msg":"Invalid username"
            }
            return jsonify(ret_json)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'),bcrypt.gensalt())

        users.insert({
            "username":username,
            "password":hashed_pw,
            "own":0,
            "debt":0
        })

        ret_json = {
            "status":200,
            "msg":"You successfully signed up for the Api"
        }

        return jsonify(ret_json)

class Transfer(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        to       = posted_data["to"]
        money    = posted_data["amount"]

        ret_json,error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        cash = cash_with_user(username)

        if cash<=0:
            return jsonify(generate_return_dictionary(304, "You're out of money, please add or take a loan"))

        if not user_exists(to):
            return jsonify(generate_return_dictionary(301, "Reciever username is invalid"))

        cash_from = cash_with_user(username)
        cash_to   = cash_with_user(to)
        bank_cash = cash_with_user('BANK')    

        update_account("BANK",bank_cash+1)
        update_account(to,cash_to+money-1)
        update_account(username,cash_from-money)

        return jsonify(generate_return_dictionary(200,"Amount Transfered successfully"))

class Balance(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        ret_json, error = verify_credentials(username,password)

        if error:
            return jsonify(ret_json)

        ret_json = users.find({
            "username":username
        },{
            "password":0,
            "_id":0
        })[0]

        return jsonify(ret_json)

class TakeLoan(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money    = posted_data["amount"]

        ret_json, error = verify_credentials(username,password)

        if error:
            return jsonify(ret_json)

        cash = cash_with_user(username)
        debt = debt_with_user(username)

        update_account(username, cash + money)
        update_debt(username, debt + money)

        return jsonify(generate_return_dictionary(200,"Loan added to your account"))

class PayLoan(Resource):
    def post(self):
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money    = posted_data["amount"]

        ret_json, error = verify_credentials(username,password)

        if error:
            return jsonify(ret_json)

        cash = cash_with_user(username)

        if cash < money:
            return jsonify(generate_return_dictionary(303,"Not enough cash in your account"))

        debt = debt_with_user(username)

        update_account(username, cash-money)
        update_debt(username, debt-money)

        return jsonify(generate_return_dictionary(200,"You've successfully paid your loan"))

api.add_resource(Register,'/register')
api.add_resource(Add     ,'/add')
api.add_resource(Transfer,'/transfer')
api.add_resource(Balance ,'/balance')
api.add_resource(TakeLoan,'/takeloan')
api.add_resource(PayLoan ,'/payload')

if __name__=="__main__":
    app.run(host='0.0.0.0')