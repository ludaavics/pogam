# -*- coding: utf-8 -*-
"""
Created on Sun Nov 10 17:30:04 2019

@author: Sam
"""

def search_seloger(projects="buy",postcode="75", rooms=2,surface="30/50",price="0/500000",lift=1,parking=1):
    """Fonction affichant pour seloger et des critères, un url de la page de recherche
    By default, to buy and it's a flat:
        types=1,2,3,11--> 1 flat, 2 house, 3 parking, 11 building
        projects=1 for rent 2 for buy
    Par defaut, cest toujours un flat 
    buy=1,postcode="75016", bedrooms=2,surfacemin=30,surfacemax=50
    
    other criterias ignored
    lastfloor=1,hearth=1,guardian=1,view=1,balcony=1/1,pool=1,terrace=1,cellar=1,south=1,box=1,parquet=1,locker=1,disabledaccess=1,alarm=1,toilet=1,
    bathtub=1/1,shower=1/1,hall=1,livingroom=1,diningroom=1,kitchen=5,heating=8192,unobscured=1,picture=15,exclusiveness=1,pricechange=1,privateseller=1,
    video=1,vv=1,enterprise=0,garden=1,basement=1):
    """
    
    #buy or rent    
    if projects=="buy":
        projects=2
    else:
        projects=1
         
    #about parking       
    if parking==1:
        parking="&parking=1"
    elif parking==0:
        parking="&parking=0"
    else:
        parking=""
        
    #about lift    
    if lift==1:
        lift="&lift=1"
    elif lift==0:
        lift="&lift=0"
    else:
        lift=""    
        
    url="https://www.seloger.com/list.html?projects="+str(projects)+"&types=1&natures=1,2&places=[{cp:"+str(postcode)+"}]&price="+str(price)+"&surface="+str(surface)+"&rooms="+str(rooms)+parking+lift+"&qsVersion=1.0"
    return url

