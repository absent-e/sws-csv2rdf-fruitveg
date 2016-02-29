#! /usr/bin/python2.7

from __future__ import division
import re
import csv
import time
import httplib
import requests
import jellyfish

myNamespace = 's1571333'
months = ['01.31', '02.29', '03.31', '04.30', '05.31', '06.30', '07.31', '08.31', '09.30', '10.31', '11.30', '12.31']

productLedger = {}
categoryLedger = {}
priceIDcount = 1

class ProductComplete:
  '''Class in which we store all the information that are going to be printed in each product file.'''
  def __init__(self, row):
    self.row = row
    self.buildProductAndOffering()
    self.priceIDs = []
    self.priceSpecs = []

##Build the strings for product and offering
  def buildProductAndOffering(self):
    uri = integrateData(self.row['ProductType'])
    self.productSpec = 	'{0}:{1} a {2}, gr:ProductOrServiceModel;\n'\
			'\tgr:name "{3}"^^xsd:string;\n'\
			'\tgr:condition "{4}"^^xsd:string.\n\n'.format(myNamespace, self.row['ID'], uri, self.row['Product'], self.row['Quality'])
    
    self.offeringSpec = '{0}:Offering{1} a gr:Offering;\n'\
			'\tgr:includes {0}:{1};\n'\
			'\tgr:validFrom "2004-01-01T00:00:00Z"^^xsd:dateTime;\n'\
			'\tgr:validThrough "2015-12-31T23:59:59Z"^^xsd:dateTime;\n'.format(myNamespace, self.row['ID'])

##Get the information needed as we go through the file
  def addPriceSpecsAndIDs(self, ids, specs):
    self.priceIDs.extend(ids)
    self.priceSpecs.extend(specs)

##Build and return the final string
  def buildStr(self):
      productStr = ''
      productStr = self.productSpec + self.offeringSpec
      productStr = productStr + '\tgr:hasUnitPriceSpecification {0}:price{1}, '.format(myNamespace, self.priceIDs[0])
      for priceID in self.priceIDs[1:-1]:
        productStr = productStr + '{0}:price{1}, '.format(myNamespace, priceID)
      productStr = productStr + '{0}:price{1}.\n\n'.format(myNamespace, self.priceIDs[-1])
      for priceSpec in self.priceSpecs:
        productStr = productStr + priceSpec
      return productStr

class Row:
  '''Class to deal with the price list in each row'''
  def __init__(self, row):
    self.row = row
    self.prices = [row['Jan'], row['Feb'], row['Mar'], row['Apr'], row['May'], row['Jun'], row['Jul'], row['Aug'], row['Sep'], row['Oct'], row['Nov'], row['Dec']] 
    self.buildUnitPriceSpec()

##Build the list of UnitPriceSpecifications and send it to the appropriate product
  def buildUnitPriceSpec(self):
    global priceIDcount
    self.priceSpecs = []
    self.priceIDs = []
    for (j, price) in enumerate(self.prices):
      if float(price) != 0:
        self.priceIDs.append(priceIDcount)
        self.priceSpecs.append(
				'{0}:price{1} a gr:UnitPriceSpecification;\n'\
				'\tgr:hasCurrency "GBP"^^xsd:string;\n'\
				'\tgr:hasCurrencyValue "{2}"^^xsd:float;\n'\
				'\tgr:hasUnitOfMeasurement "{3}"^^xsd:string;\n'\
				'\tgr:validFrom "{4}-{5}-01T00:00:00Z"^^xsd:dateTime;\n'\
				'\tgr:validThrough "{4}-{5}-{6}T23:59:59Z"^^xsd:dateTime.\n\n'.format(myNamespace, priceIDcount, price, self.row['Units'], self.row['Year'], months[j][:2], months[j][3:]))
        priceIDcount += 1
    try:##Send the list to the product
      productLedger[row['ID']].addPriceSpecsAndIDs(self.priceIDs, self.priceSpecs)
    except:
      print "Failing."

### Data Integration using the ProductOntology ###
def integrateData(thingName):
  #Manual matching of five resources
  if thingName == 'Shelling Peas':
    return '<http://www.productontology.org/doc/Snap_pea>'
  elif thingName == 'Asian Lillies':
    return '<http://www.productontology.org/doc/Lilium>'
  elif thingName == 'Chrysanthemums Flowers':
    return '<http://www.productontology.org/doc/Chrysanthemum>'
  elif "Soleil" in thingName:
    return '<http://www.productontology.org/doc/Narcissus_(plant)>'
  elif thingName == 'Oriental Lilies':
    return '<http://www.productontology.org/doc/Lilium>'

  #Do a tiny bit of cleaning
  if re.search(r'(.*) (or|and) (.*)', thingName):#Only take the second of the words/group of words when there is "x and|or y"
    thingMatch = re.search(r'(.*) (or|and) (.*)',  thingName)
    thingName = thingMatch.group(3)
  if re.search(r'(.*)-.*', thingName):#Only take the part before '-'
    thingMatch = re.search(r'(.*)-.*',  thingName)
    thingName = thingMatch.group(1)

  #From plural to singular: handle different cases
  if re.search(r'(.*)ies$', thingName):
    thingName = re.sub(r'(.*)ies$', r'\1y', thingName)
  elif re.search(r'(.*)oes$', thingName):
    thingName = re.sub(r'(.*)oes$', r'\1o', thingName)
  elif re.search(r'(.*)ses$', thingName):
    thingName = re.sub(r'(.*)ses$', r'\1s', thingName)
  elif re.search(r'(.*)s$', thingName) and thingName != 'Asparagus' and thingName != 'Watercress':
    thingName = re.sub(r'(.*)es$', r'\1e', thingName)
  elif re.search(r'(.*)s$', thingName) and thingName != 'Asparagus' and thingName != 'Watercress':
    thingName = re.sub(r'(.*)s$', r'\1', thingName)
  originalThing = thingName.title().replace(' ', '')#What we'll return if we don't find anything
  thingName = re.sub(' ', '_', thingName)#Spaces removed for lookup (URL)
  thingName = thingName.lower()#Lowercase for lookup

  #Get info from the Product Ontology using the name we came up with
  r = requests.get("http://www.productontology.org/doc/{0}".format(thingName))
  if r.status_code == 200:#Return URI if it is a valid name
    return '<{0}>'.format(r.url)
  else:
    return thingName


##Go through the whole file, build the data structure
with open('cleanest_fruitveg.csv', 'r') as csvf:
  fruitvegReader = csv.DictReader(csvf, delimiter = ',')
  for (i, row) in enumerate(fruitvegReader):
    if row['ID'] not in productLedger.keys():
      x = ProductComplete(row)
      productLedger[row['ID']] = x
    if row['Category'] not in categoryLedger.keys():
      categoryLedger[row['Category']] = [row['ProductType']]
    elif row['ProductType'] not in categoryLedger[row['Category']]:
      categoryLedger[row['Category']].append(row['ProductType'])
    i = Row(row)

categorySpecs = []

#Build the categories and Product Type triples
for category in categoryLedger.keys():
  categorySpecs.append(	'{0}:{1} a owl:class, gr:ProductOrService;\n'\
			'\trdfs:label "{2}"^^xsd:string.\n\n'.format(myNamespace, category, category))
  for productType in categoryLedger[category]:
    uri = integrateData(productType)
    categorySpecs.append(	'{1} a {0}:{2}, gr:ProductOrService;\n'\
				'\trdfs:label "{3}"^^xsd:string.\n\n'.format(myNamespace, uri, category, productType))

#Build the prefixes
prefixes = 	'@prefix {0}: <http://vocab.inf.ed.ac.uk/sws/{0}/{0}#>.\n'\
		'@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.\n'\
		'@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.\n'\
		'@prefix owl: <http://www.w3.org/2002/07/owl#>.\n'\
		'@prefix gr: <http://purl.org/goodrelations/v1#>.\n\n'.format(myNamespace)

##Write the structure to file
with open('fruit_veg_ontology.ttl', 'a') as o:
  o.write(prefixes)
  for k in categorySpecs:
    o.write(k)
  for p in productLedger.keys():
    o.write(productLedger[p].buildStr())


