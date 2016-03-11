# This is a Python scraper on morph.io (https://morph.io)
# It scrapes data from the AEC "media feed" FTP service

import scraperwiki
from ftplib import FTP
from zipfile import ZipFile
from lxml import etree
import urllib
import io

FTP_URL = 'results.aec.gov.au'
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

		# Write out to the sqlite database using scraperwiki library
		for election in elections['elections']:
			data = {'id': elections['id'], 'name': elections['name']}
			data.update(election)
			print(data)
			scraperwiki.sqlite.save(unique_keys=['id', 'category'], data=data)

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
	election_id = event.get('Id')
	election_name = event.find('eml:EventName', NS).text
	elections = xml.xpath('.//aec:Election', namespaces=NS)
	elections_data = [election_data(election) for election in elections]
	return {'id': election_id, 'name': election_name, 'elections': elections_data}

# This function takes an lxml object and returns election (House of Reps. or Senate) data
def election_data(xml):
	election = xml.find('eml:ElectionIdentifier', NS)
	name = election.find('eml:ElectionName', NS).text
	category = election.find('eml:ElectionCategory', NS).text
	return {'name': name, 'category': category}

if __name__ == '__main__':
	# Load up the FTP service
	ftp = FTP(FTP_URL)
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
			latest_file = files[0]
			sock = urllib.urlopen('ftp://{url}{path}/{file}'.format(url=FTP_URL, path=path, file=latest_file))
			extract_data(io.BytesIO(sock.read()), election_id)
