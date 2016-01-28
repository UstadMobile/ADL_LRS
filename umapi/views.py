from django.shortcuts import render
from django.conf import settings
from django.contrib.auth import authenticate

from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.contrib import auth
from django.template import RequestContext
from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.core import serializers
from models import statement_forward_status
from models import credentials
from lrs.models import Statement
import urllib2, base64, json
from jsonfield import JSONField
import httplib
import os

def root_view(request):
    print("Hey there")
    authresponse = HttpResponse(status=200)
    authresponse.write("Root here, seems to be working..")
    return authresponse

def xapi_login(username, password, url):
    req = urllib2.Request(url)
    req.add_header("X-Experience-API-Version", "1.0.1")
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % base64string)
    
    try:
        response = urllib2.urlopen(req)
        response_code = response.getcode()
	if response.getcode() == 200:
	    print("Statement status 200")
	    return True
	    
    except urllib2.HTTPError, e:
        print('HTTPError = ' + str(e.code))
	response_code = e.code
	return False

    except urllib2.URLError, e:
        print('URLError = ' + str(e.reason))
    except httplib.HTTPException, e:
        print('HTTPException')
    except Exception, e:
        print('generic exception: ' + str(e) )
	response_code = response.getcode()
	if response_code == 200:
	    print("Success.")
	    return True

    #return response_code

    return False

def auth_backend(username, password, master_server_url):
    try:
        print("Checking your Login..")
	user = User.objects.get(username=username)
    except User.DoesNotExist:
	print("User does not exist..")
	user = None

    #try:
    if True:
	user_destination = username + "@" + master_server_url
        #Check username and password here..
	user = authenticate(username=username, password=password)
	if user is not None:
	    # Yes? return the Django user object
	    print("Local LRS: Username and Password check success")
	    print("Not so fast, it could be old password. Will check the same against the Master Server..")
	    if xapi_login(username,password, master_server_url): 
		#Returns true if user is successfully authenticated, False if not
		print("Master Server: Username and Password check success.")
		print("   Nothing to update. Letting you through..")
	        return user
	    else:
		print("Master Server: Unable to check same credentials on Master Server. Either password is wrong on either master/local or no account created.")
		return None
	else:
	    print("Local LRS: User auth failed.")
	    print("Local LRS: Checking if user exists at all on local LRS..")
	    user_count = User.objects.filter(username=username).count()
            if user_count > 0:
		print("Local LRS: Okay, so the user exists locally. The password given was locally wrong but may be okay on the Master Server") 
		if xapi_login(username,password, master_server_url):
		    print("Master Server: The password was correct here")
		    print("   got to update local's password")
		    user = User.objects.get(username=username)
		    user.set_password(password)
		    user.save()
		    print("     updated. Updating credentials")
		    #update credentials as well.
		    try:
		        credential_map = credentials.objects.get(user_destination=user_destination)
		        if credential_map is not None:
			    credential_map.password = password
			    credential_map.save()
			    print("         updated credentials.")
		    except credentials.DoesNotExist:
			print("Cred not existing. Making one..")
			new_credential = credentials(username=username, endpoint=master_server_url, user=user,user_destination=user_destination, password=password)
             		new_credential.save()
		    except Exception, e:
			print("Unable to get credential map")
			print("Reason : " + str(e))
		    
		return user		
	    else:
		print("Local LRS: Nope, no user locally. Checking on Master Server")
	        if xapi_login(username,password, master_server_url): 
		    #Returns true if user is successfully authenticated, False if not
		    print("Master Server: Username and Password check success for new user.")
		    print("Master Server: Will Create New User")
		    #Create user.
		
		    user_email = username + "@email.com"
		    user = User(username=username, email=user_email)
		    user.set_password(password)
		    user.is_active = True
		    user.save()
		    print("User created!")
		    return user;
	        else:
		    print("Master Server: Credential login failed / No user found")
		    return None

    else:
    #except Exception, e:
	print("Exception: " + str(e))



def auth_backend_old(username, password, master_server_url):
    if xapi_login(username,password, master_server_url): 
        #Returns true if user is successfully authenticated, False if not
	print("Username and Password check success for new user.")
	print("Checking new user in Django..")
	#Create user.
	user_count = User.objects.filter(username=username).count()
        if user_count == 0:
	    print ("User doesn't exist, creating user..")
	    user = User(username=username, email=username)
    	    user.set_password(password)
	    user.is_active = True
            user.save()
	    print("User created!")
	    return user;
        else:
       	    #Show message that the username/email address already exists in our database.
	    print("Error in creating user. User already exists!..")

	    user = authenticate(username=username, password=password)
	    if user is None :
		print("Password needs updating on local db..")
	    	user = User.objects.get(username=username)
	    	user.set_password(password)
	    	user.save()
		print("Updated.")
		user_destination = username + "@" + master_server_url
		credential_map = credentials.objects.get(user_destination=user_destination)
		if credential_map is not None:
		    credential_map.password = password
		    credential_map.save()

	    return user;
    else:
	print("Username and Password check unsuccessfull for new user. Not creating new user.")
        print("Maybe its present locally ?")
    
    try:
        print("Checking on local database..")
	user = User.objects.get(username=username)
        #Check username and password here..
	user = authenticate(username=username, password=password)
	if user is not None:
	    # Yes? return the Django user object
	    print("Username and Password check success")
	    return user
	else:
	    # No? return None - triggers default login failed
	    print("Username and Password check unsuccessfull")
            print("Local username and password dont match or username does not exist")
            return None

    except User.DoesNotExist:
	print("User does not exist in local DB as well.")
	return None
    except Exception, e:
	print("Exception in getting local user if exists:" + str(e))
	return None

"""
external facing API: POST request. Send me "username", "password" "url" < Thats the master server. 

"""
def login(request):
    try:
        username = request.POST['username']
        password = request.POST['password']
        master_server_url = request.POST['url']
	url = master_server_url
    except:
	print("I'm testing..")
        username="varunasingh"
        password="varunasingh"
        master_server_url = "http://localhost:8044/xAPI/statements"
	limit_bit = "?limit=1"
	url = os.path.join(master_server_url, limit_bit)
	authresponse = HttpResponse(status=400)
	authresponse.write("Bad request. Make sure username, password, and master server url are in this request as POST")
	return authresponse
	

    if not master_server_url.endswith("/"):
	master_server_url = master_server_url + "/"
    user_destination = username + "@" + master_server_url

    print("Checking user: " + username)
    user = auth_backend(username, password, url)
                
    if user is None:
	authresponse = HttpResponse(status=401)
	authresponse.write("Invalid login")
	return authresponse
    else:
	print("checking all cred against : " + user_destination)
        all_credentials = credentials.objects.values_list("user_destination", flat=True)
        if user_destination not in all_credentials:
            print("Creating new credential..")
            new_credential = credentials(username=username, endpoint=master_server_url, user=user, user_destination=user_destination, password=password)
            new_credential.save()
            print("Created new credential.")
	authresponse = HttpResponse(status=200)
	authresponse.write("Login OK")
	return authresponse

#@login_required(login_url='/accounts/login/')
def forward(request):
    print "Starting forward for every user.."
    all_users = User.objects.all()
    for every_user in all_users:
	username = every_user.username
	print("Scanning statements for user: " + str(username))
	try:
	    user_credential = credentials.objects.get(user=every_user, username=username)
	except credentials.DoesNotExist:
	    print("Skipping out for username: " + str(username))
	    #Skipping because this user has no credetials stored. Whih means user has not logged in 
	    #the user couldn't have made any statements. We have this because when the user logs in
	    #We keep the server url by which he wants to log in. That way we know fr sure where the
	    #statements should go (ie the master server)
	    continue
	password = user_credential.password

        all_pending_statement_status = update_statement_forward_status(every_user, user_credential)

        for every_statement_status in all_pending_statement_status:
	    sendStatement(every_statement_status)

    authresponse = HttpResponse(status=200)
    authresponse.write("Forwarded.")
    return authresponse

def update_statement_forward_status(user, user_credential):
    all_user_statements = Statement.objects.filter(user=user)
    for every_statement in all_user_statements:	
	if every_statement.id not in statement_forward_status.objects.values_list('statement', flat=True):
	    print("So, " + str(every_statement.id) + " is not in " + str(statement_forward_status.objects.values_list('statement', flat=True)))
	    print("Not in")
	    statement_status = statement_forward_status(statement=every_statement, credential=user_credential)
            statement_status.save()
	else:
	    #print("Its in!")
	    pass

    all_pending_statements_status = statement_forward_status.objects.filter(status="pending")
    return all_pending_statements_status

def sendStatement(statement_status):
    #Make post request
    # Got to do request commands or something similar
    statement = statement_status.statement
    username = statement_status.credential.username
    password = statement_status.credential.password
    url = statement_status.credential.endpoint
    if url.endswith("?limit=1"):
	url = url.split("?limit=")[0]
    #MASTER_SERVER_XAPI="http://localhost:8044/xAPI/statements/"
    #url = "http://localhost:8044/xAPI/statements/"
    MAX_PENDING_TRIES=20

    req = urllib2.Request(url)
    req.add_header("X-Experience-API-Version", "1.0.1")
    base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
    req.add_header("Authorization", "Basic %s" % base64string)   
    statement_json = statement.full_statement
    #Need to do it as ADL doesn't recognize stored when sending new statement to another LRS server
    del statement_json['stored']

    statement_json_string = json.dumps(statement_json)
    print("Statement JSON STRING:")
    print(statement_json_string)

    try:
        response = urllib2.urlopen(req,statement_json_string)
	response_code = response.getcode()
	if response.getcode() == 200:
	    print("Statement status 200")
	    statement_status.tries = statement_status.tries + 1
	    statement_status.status = "sent"
	    statement_status.save()
	    
    except urllib2.HTTPError, e:
        print('HTTPError = ' + str(e.code))
	response_code = e.code
	statement_status.response = str(response_code)
	statement_status.tries = statement_status.tries + 1
        statement_status.save()

	if str(e.code).startswith("4"):
	    if e.code == 409:
		print("Statement already exists in system.")
		statement_status.status = "sent"
		statement_status.save()

	    print(str(statement_status.tries))
	    if statement_status.tries > MAX_PENDING_TRIES:
		print("Maxed out")
		statement_status.response = statement_status.response + " MAXED"
		statement_status.status = "fail"
		statement_status.save()

	    if e.code == 401:
		print("Unauthorized. Will have to try again.")
	    else:
		print("Will try again..")
		print(str(e))
	if e.code == 500:
	    print("Most certainly a fail.")
	    statement_status.status = "fail"
	    statement_status.save()

	else:
	    print("Unable to determine what the response was..")
    except urllib2.URLError, e:
        print('URLError = ' + str(e.reason))
    except httplib.HTTPException, e:
        print('HTTPException')
    except Exception, e:
        print('generic exception: ' + str(e) )
	response_code = response.getcode()
	if response_code == 200:
	    print("Success.")
	    statement_status.tries = statement_status.tries + 1
	    statement_status.status = "sent"
	    statement_status.save()

    #return response_code

def statements_proxy(request):
    print("hey")
    username = ""
    password = ""
    

# Create your views here.
