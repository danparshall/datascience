import twitter
import MySQLdb as sql
from matplotlib.pyplot import pause

# Playing around with the Twitter API, this checks to see if @KevinBacon is following you. 
# Actually, it checks to see if @KevinBacon is following someone who is following someone 
# who is following someone who is following you. But that's 4 degrees of separation, which 
# is practically stalker-level in KevinBacon terms.
#
# First step was to generate SQL database containing the "follwees" akea "friends" of 
# @KevinBacon (those having a BaconFollowNumber of 1).  An additional table stores
# those who are Friends of the Friends of KevinBacon (i.e., rank2).  Storing the
# noxt step is incomplete, and needs to wait until some checks are in place to eliminate
# redundant calls to the rate-limited Twitter API.
# 
# Nevertheless, by comparing a "targetUser" of interest with just those two tables,
# we can check through Rank3 BaconNumbers.  By pulling the Followers of the TargetUser,
# this can check up through Rank4.  So far this has been sufficent for all of the cases.

# kevin bacon's userID :
baconID = 348785149

## TODO : 
#	standardize tables with screen_name, connectingID, etc for all
#	cache screen_name to database upon lookup
#	define function to call for screen_name, check up the chain
#	add some optimization to exclude redundancy (rank3 who are already rank2, etc)
#	could reverse the graph, but might have to filter out users with more than 2k fols allowed using "celebrities_profiles.txt" from Korean group
#	error handling


############################################

# secret data kept in separate file
with open('twitdat.txt') as f:
    fromFile = {}
    for line in f:
        line = line.split() # to skip blank lines
        if len(line)==3 :			# 
			fromFile[line[0]] = line[2]			
f.close()

api = twitter.Api(consumer_key = fromFile['consumer_key'],
consumer_secret = fromFile['consumer_secret'],
access_token_key = fromFile['access_token_key'],
access_token_secret = fromFile['access_token_secret'])
targetUser = fromFile['targetUser']

db = sql.connect(db='dbacon')

# see http://www.bacon-number.com/bacon-number-calculator/
# see http://zetcode.com/db/mysqlpython/


################################################################################
class Table:
	def __init__(self, db, name):
		self.db = db
		self.name = name
		self.dbc = self.db.cursor()
	def additem(self, user_id, screen_name):
		ins = "INSERT INTO " + self.name + " VALUES(" + str(user_id) + ", '" + str(screen_name) + "')"
#		print ins
		rows = self.dbc.execute(ins)
#		print rows
		return
	def addlink(self, user_id, link_id):
		ins = "INSERT INTO " + self.name + " VALUES(" + str(user_id) + ", " + str(link_id) + ")"
#		print ins
		rows = self.dbc.execute(ins)
#		print rows
		return

###############################################################################
## builds SQL database of people followed by Kevin Bacon (@kevinbacon), who are 
#	"rank1".  The people who follow rank1 are "rank2", etc.
def buildBaconBase(db):
	print api.VerifyCredentials()

	frnd = Table(db, 'friends')
	rank2 = Table(db, 'rank2')
	rank3 = Table(db, 'rank3')


	# fetch BaconNumber of 1
	rank1 = api.GetFriendIDs(screen_name='kevinbacon')
	for friend in rank1:
		frnd.additem(friend,'bacon1')
	db.commit()


	# generate BaconNumber of 2
	kbF2 = {}
	iB1 = 0
	for friend in rank1:
		print friend, type(friend)
		pause(60)				# twitter rate-limits these requests

		try:
			newCircle = api.GetFriendIDs(user_id=friend)

			kbF2[friend] = newCircle
			for link in newCircle:
				rank2.addlink(link,friend)
			db.commit()
		except:
			print iB1
			print newCircle

		iB1 = iB1 + 1
		db.commit()


	# generate BaconNumber of 3
	kbF3={}
	for friend in rank2:
		pause(60)
		newCircle = api.GetFriendIDs(user_id = friend)

		kbF3[friend] = newCircle
		for link in newCircle:
			rank3.addlink(link, friend)
		db.commit()

################################################################################
def showTables(db):
	cur = db.cursor()
	nRows = cur.execute('show tables;')		# stores rows within cur

	for idx in range(nRows):				# print rows one by one
		print cur.fetchone()

	nRows = cur.execute('show tables;')		# stores rows within cur
	tables = cur.fetchall()					# store all rows in tuple
	return tables


################################################################################
def readRank1(db):
	friends = []
	cur = db.cursor()
	nFriends = cur.execute('select user_ID from friends;')

	for idx in range(nFriends):
		friends.append(cur.fetchone()[0])	# list of all elements (198 long)
	return friends


################################################################################
## make dict with rank2 values.  Only actually need this to create rank3 if 
#	process is interrupted
def readRank2(db):
	rank2 = {}
	cur = db.cursor()
	nR2 = cur.execute('select * from rank2;')

	if nR2 == 0:
		print 'Table is empty; needs to be generated.'
	else:
		for idx in range(nR2):
			row = cur.fetchone()
			rank2[ row[0] ] = row[1]
	return rank2


################################################################################
def traceFriends(userID, trace, db):
#	trace = []
	cur = db.cursor()

	# user is kevinbacon
	if userID == baconID:
		print "Link found to @KevinBacon!"
		trace.append(userID)

	else:
		# check for userID in rank1 table
		cmd = 'select screen_name from friends where user_ID = ' + str(userID)
		r1 = cur.execute(cmd)

		if r1 > 0:	# if found in Rank1, add to trace list
			trace.append(userID)

		else :
			# check for userID in rank2 table
			cmd = 'select connectingID from rank2 where user_ID = ' + str(userID)
			r2 = cur.execute(cmd)

			if r2 > 0:	# if found, add to trace, then recurse
				trace.append(userID)
				nextLinkCmd = 'select connectingID from rank2 where user_ID = ' + str(userID)
				nNext = cur.execute(nextLinkCmd)
				if nNext > 0:
					traceFriends( cur.fetchone()[0], trace, db)
				else :
					print "Error in the BaconGraph.  This may be corrected later."

			else :		
				# check rank3 table
				cmd = 'select connectingID from rank3 where user_ID = ' + str(userID)
				r3 = cur.execute(cmd)

				if r3 > 0:
					trace.append(userID)
				else :
#					print "no link found :("		
					pass
	return trace

################################################################################
def checkTarget(targetID):
	trace = []

	trace = traceFriends(targetID, trace, db)

	if len(trace)==0:
		tarFol = api.GetFollowerIDs(targetID)

		for fol in tarFol:
			trace = traceFriends(fol, trace, db)

			if len(trace)>0:

				targetName = api.GetUser(targetID).GetScreenName()
				print targetName, "is followed by:"
				for ind in range(len(trace)):
					chainName = api.GetUser(trace[ind]).GetScreenName()
					print chainName, "who is followed by:"
				
				print "KevinBacon"
				break

	else :
		print targetName, "has escaped the notice of @KevinBacon"

	return trace

################################################################################


targetName = 'GrimBrotherOne'		# default
targetID = api.GetUser(screen_name=targetName).GetId()
print targetName, targetID

trace = checkTarget(targetID)


