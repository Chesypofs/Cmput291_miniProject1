import cx_Oracle
import sys
import random

# Connects to the database and returns the connection object
def getConnection():
	f = open('connection.txt')
	username = f.readline().strip()
	password = f.readline().strip()
	f.close()
	try:
		return cx_Oracle.connect(username, password, "gwynne.cs.ualberta.ca:1521/CRS")
	except cx_Oracle.DatabaseError as exc:
		error = exc.args
		print(sys.stderr, "Oracle code:", error.code)
		print(sys.stderr, "Oracle message:", error.message)
		sys.exit()

# Trys to log in using a user id and password
# On success returns the user id, else returns false		
def login(connection):
	while (True):
		user_id = input("Please input your user id: ")
		try:
			user_id = int(user_id)
			break
		except ValueError:
			print("User id must be an integer.")
	user_password = input("Please input your password: ")
	curs = connection.cursor()
	curs.prepare("select * from users where usr = :id and pwd = :password")
	curs.execute(None, {'id':user_id, 'password':user_password})
	if curs.fetchone():
		curs.close()
		return user_id
	else:
		curs.close()
		return False

# Creates a new account and returns the user id given by the system		
def createAccount(connection):
	user_name = ""
	user_email = ""
	user_city = ""
	user_timezone = 0
	user_password = ""
	user_id = random.randrange(-2147483648, 2147483647) #-2^31 to (2^31)-1
	while (True):
		user_name = input("Please input a name: ")
		if len(user_name) > 20:
			print("Maximum length of name is 20.")
		else:
			break
	while (True):
		user_email = input("Please enter an email: ")
		if len(user_email) > 15:
			print("Maximum length of email is 15.")
		else:
			break
	while (True):
		user_city = input("Please enter a city: ")
		if len(user_city) > 12:
			print("Maximum length of city is 12.")
		else:
			break
	while (True):
		user_timezone = input("Please enter a timezone: ")
		try:
			user_timezone = float(user_timezone)
			break
		except ValueError:
			print("Timezone must be a float.")
	while (True):
		user_password = input("Please enter a password: ")
		if len(user_password) > 4:
			print("Maximum length of password is 4.")
		else:
			break
			
	# Check that the user id is unique
	while (True):
		curs = connection.cursor()
		curs.prepare("select * from users where usr = :id")
		curs.execute(None, {'id':user_id})
		if curs.fetchone():
			user_id = random.randrange(-2147483648, 2147483647)
			curs.close()
		else:
			print("User id is: ", user_id)
			curs.close()
			break
	
	curs = connection.cursor()
	curs.prepare("insert into users values (:id, :pwd, :name, :email, :city, :timezone)")
	curs.execute(None, {'id':user_id, 'pwd':user_password, 'name':user_name, 'email':user_email, 'city':user_city, 'timezone':user_timezone})
	curs.close()
	return user_id

# Returns all tweets/retweets from users that the logged in user follows
def getTweetsFromFollowedUsers(connection, user_id):
	curs = connection.cursor()
	curs.prepare("select * from "
				"((select t.tid, t.writer, t.tdate, t.text "
				"from follows f, tweets t "
				"where f.flwer = :id and t.writer = f.flwee) "
				"union (select t.tid, t.usr as writer, t.rdate as tdate, ot.text " 
				"from follows f, retweets t, tweets ot "
				"where f.flwer = :id and t.usr = f.flwee and t.tid = ot.tid)) "
				"order by tdate")
	curs.execute(None, {'id':user_id})
	rows = curs.fetchall()
	curs.close()
	return rows

# Returns the number of retweets and replies for the tweet	
def getTweetStats(connection, tweet_id):
	curs = connection.cursor()
	curs.prepare("select (select nvl(count(*), 0) from tweets where replyto = :tid1) as num_tweets, "
		"(select nvl(count(*), 0) from retweets where tid = :tid2) as num_retweets from dual")
	curs.execute(None, {'tid1':tweet_id, 'tid2':tweet_id})
	row = curs.fetchone()
	curs.close()
	return row
	
def main():
	connection = getConnection()
	user_id = False
	created_new_account = False
	
	# Log in or create an account
	while (True):
		inp = input("Type 'login' to login, 'create' to create an account, or 'exit' to exit: ")
		if inp == "exit":
			connection.close()
			sys.exit()
		elif inp == "login":
			user_id = login(connection)
			if (user_id == False):
				print("Invalid user id/password.")
			else:
				print("Successfully logged in.")
				break
		elif inp == "create":
			user_id = createAccount(connection)
			connection.commit()
			created_new_account = True
			print("Successfully created an account and logged in.")
			break
		else:
			print("Unrecognized input, please try again.")
	
	# User logged in, get the new tweets/retweets from the users the logged in user follows
	row_buffer = []
	if not created_new_account:
		rows = getTweetsFromFollowedUsers(connection, user_id)
		print("New tweets/retweets from the users you follow:")
		i = 0
		finished = False
		for row in rows:
			row_buffer.append(row)
			i = i + 1
			if i > 5:
				inp = ""
				while (True):
					inp = input("Type numbers 1-5 to view more information about the tweet, "
						"'more' to view the next 5 tweets, or 'skip' to skip viewing the tweets: ")
					if inp != "skip" and inp != "more" and inp != "1" and inp != "2" and inp != "3" and inp != "4" and inp != "5":
						print("Unrecogzied input, please try again.")
					else:
						break
				if inp == "skip":
					finished = True
					break
				elif inp == "more":
					i = 0
					row_buffer = []
					continue
				# A tweet was selected
				else:
					stats = getTweetStats(connection, row_buffer[int(inp)][0])
			else:
				print(i, row)
		
		# There was not 5 tweets/retweets to print out
		if not finished:
			print(row_buffer)
			while (True):
				inp = ""
				if i > 1:
					inp = input("Type numbers 1-%s to view more information about the tweet, "
						"or 'skip' to skip viewing the tweets: " % (i))
				else:
					inp = input("Type number 1 to view more information about the tweet, "
						"or 'skip' to skip viewing the tweets: ")
				if inp == "1" or inp == "2" or inp == "3" or inp == "4" or inp == "5":
					if int(inp) > i:
						print("There is no tweet number %s, please try again." % (inp))
					# A tweet was selected
					else:
						stats = getTweetStats(connection, row_buffer[int(inp)][0])
				elif inp == "skip":
					break
				else:
					print("Unrecognized input, please try again.")
					
	connection.commit()
	connection.close()

if __name__ == "__main__":
	main()