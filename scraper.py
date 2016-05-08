# This is a Python scraper on morph.io (https://morph.io)
# It scrapes data from the AEC "media feed" FTP service

import scraperwiki
from ftplib import FTP
from zipfile import ZipFile
from lxml import etree
import urllib
import io

FTP_URL = 'results.aec.gov.au'
FTP_TIMEOUT = 30
NS = {
	'aec': 'http://www.aec.gov.au/xml/schema/mediafeed',
	'eml': 'urn:oasis:names:tc:evs:schema:eml'
}

# This function reads in data from the "media feed" XML
# then extracts the data and writes it to the database
def extract_data(file, id):
		# Get the XML file from the zip data
		xml = unzip_xml(file, id)

		# Read in the data from the XML
		elections = elections_data(read_xml(xml))

# This function gets the "media feed" XML from its zip file
def unzip_xml(file, id):
	with ZipFile(file, 'r') as feed_zip:
		with feed_zip.open('xml/aec-mediafeed-results-detailed-verbose-{id}.xml'.format(id=id)) as xml:
			return xml

# This function reads in data from the "media feed" XML
def read_xml(file):
	xml = etree.parse(file)
	return xml.getroot()

# This function takes an lxml object and returns all (House of Reps. and Senate) election data
def elections_data(xml):
	results = xml.find('aec:Results', NS)
	event = results.find('eml:EventIdentifier', NS)
	id = event.get('Id')
	name = event.find('eml:EventName', NS).text
	elections = xml.xpath('.//aec:Election', namespaces=NS)
	elections_data = [election_data(election, id) for election in elections]

	scraperwiki.sqlite.save(table_name='event',
		unique_keys=['id', 'name'],
		data={'id': id, 'name': name})

	return {'id': id, 'name': name, 'elections': elections_data}

# This function takes an lxml object and returns election (House of Reps. or Senate) data
def election_data(xml, event_id):
	election = xml.find('eml:ElectionIdentifier', NS)
	id = election.get('Id')
	name = election.find('eml:ElectionName', NS).text
	category = election.find('eml:ElectionCategory', NS).text
	contests = xml.xpath('.//aec:Contest', namespaces=NS)
	contests_data = [contest_data(contest, event_id, id) for contest in contests]

	scraperwiki.sqlite.save(table_name='election',
		unique_keys=['event_id', 'id'],
		data={'event_id': event_id, 'id': id, 'name': name, 'category': category})

	return {'id': id, 'name': name, 'category': category, 'contests': contest_data}

# This function takes an lxml object and returns contest (e.g., a single electorate's election) data
def contest_data(xml, event_id, election_id):
	contest = xml.find('eml:ContestIdentifier', NS)
	id = contest.get('Id')
	name = contest.find('eml:ContestName', NS).text
	enrolment = int(xml.find('aec:Enrolment', NS).text)

	# First preference data
	first_preferences = xml.find('aec:FirstPreferences', NS)
	candidates = first_preferences.xpath('.//aec:Candidate', namespaces=NS)
	candidates_data = [candidate_data(candidate, event_id, election_id, id, 'first_preferences') for candidate in candidates]

	# Two candidate preference data
	two_candidate_preferred = xml.find('aec:TwoCandidatePreferred', NS)
	if two_candidate_preferred is not None:
		candidates = two_candidate_preferred.xpath('.//aec:Candidate', namespaces=NS)
		candidates_data = [candidate_data(candidate, event_id, election_id, id, 'two_candidate_preferred') for candidate in candidates]

	scraperwiki.sqlite.save(table_name='contest',
		unique_keys=['event_id', 'election_id', 'id'],
		data={'event_id': event_id, 'election_id': election_id, 'id': id, 'name': name, 'enrolment': enrolment})

	return {'id': id, 'name': name, 'enrolment': enrolment, 'candidates': candidates_data}

# This function takes an lxml object and returns candidate data
def candidate_data(xml, event_id, election_id, contest_id, kind):
	candidate = xml.find('eml:CandidateIdentifier', NS)
	id = candidate.get('Id')
	name = candidate.find('eml:CandidateName', NS).text

	elected = boolean_text(xml.find('aec:Elected', NS).text)
	incumbent = boolean_text(xml.find('aec:Elected', NS).text)
	votes = int(xml.find('aec:Votes', NS).text)

	party = party_data(xml)

	scraperwiki.sqlite.save(table_name='candidate',
		unique_keys=['id'],
		data={'id': id, 'name': name})

	scraperwiki.sqlite.save(table_name=kind,
		unique_keys=['event_id', 'election_id', 'contest_id', 'candidate_id'],
		data={'event_id': event_id, 'election_id': election_id, 'contest_id': contest_id, 'candidate_id': id, 'party_id': party.get('id'),
			'elected': elected, 'incumbent':  incumbent, 'votes': votes})

	return {'id': id, 'name': name, 'elected': elected, 'incumbent': incumbent, 'first_preferences': votes, 'party': party}

# This function takes an lxml object and returns party data
def party_data(xml):
	party = xml.find('eml:AffiliationIdentifier', NS)

	if party is not None:
		id = party.get('Id')
		code = party.get('ShortCode')
		name = party.find('eml:RegisteredName', NS).text

		scraperwiki.sqlite.save(table_name='party',
			unique_keys=['id'],
			data={'id': id, 'code': code, 'name': name})
		
		return {'id': id, 'code': code, 'name': name}
	
	else:
		return {}

# this function turns a 'true' or 'false' string into a boolean
def boolean_text(string):
	if string == 'true':
		return True
	elif string == 'false':
		return False
	else:
		return None

if __name__ == '__main__':
	# Load up the FTP service
	ftp = FTP(FTP_URL, timeout=FTP_TIMEOUT)
	ftp.login()

	# Get the list of elections with data
	election_ids = ftp.nlst()

	# Retrieve the data in each election's directory
	for election_id in election_ids:
		# go to the directory
		path = '/{id}/Detailed/Verbose/'.format(id=election_id)
		ftp.cwd(path)
		# Get the files ordered by time
		files = ftp.nlst('-t')

		if files:
			# Download the latest file and extract the data
			latest_file = files[-1]
			sock = urllib.urlopen('ftp://{url}{path}/{file}'.format(url=FTP_URL, path=path, file=latest_file))
			extract_data(io.BytesIO(sock.read()), election_id)
