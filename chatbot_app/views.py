from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from pydialogflow_fulfillment import DialogflowResponse
from pydialogflow_fulfillment.response import SimpleResponse, OutputContexts
from bs4 import BeautifulSoup
from requests import get
import pandas as pd
from chatbot_app.models import globalStatus, globalLastUpdate, MOHHeadlines, hospitalList
from WebScrape import statusScrapper, newsScrapper
from django import db
import googlemaps
from datetime import datetime
gmaps = googlemaps.Client(key = 'AIzaSyCpqFU-7MTe4GSgFzuobfscIYm1E-tLrgY')


# Create your views here.

def index(request):
    my_dict = {'variable': "Hello World"}
    return render(request, r'chat_bot_template/index.html', context= my_dict)

@csrf_exempt
def webhook(request):
    # build a request object
    req = json.loads(request.body)
    # get action from json
    intent = req.get('queryResult').get('intent').get('displayName')

    # --------------------------#
    # INFECTION STATUS INTENT   #
    # --------------------------#
    if intent == "infection-status-covid":
        country = req.get('queryResult').get('parameters').get('country-defined')
        casestatus = req.get('queryResult').get('parameters').get('CaseStatus')

        pd_table = pd.DataFrame(list(globalStatus.objects.all().values()))
        LastUpdate = list(globalLastUpdate.objects.all().values('last_update'))[0]['last_update']

        try:
            diagnose_ = pd_table[pd_table['country'] == country]['diagnosed'].iloc[0]
            death_ = pd_table[pd_table['country'] == country]['death'].iloc[0]
            discharged_ = pd_table[pd_table['country'] == country]['discharged'].iloc[0]
            active_ = pd_table[pd_table['country'] == country]['active'].iloc[0]
            critical_ = pd_table[pd_table['country'] == country]['critical'].iloc[0]
            new_case_ = pd_table[pd_table['country'] == country]['new_cases'].iloc[0]
            new_death_ = pd_table[pd_table['country'] == country]['new_death'].iloc[0]
            
        except:
            country = "Worldwide"
            diagnose_ = pd_table[pd_table['country'] == 'total:']['diagnosed'].iloc[0]
            death_ = pd_table[pd_table['country'] == 'total:']['death'].iloc[0]
            discharged_ = pd_table[pd_table['country'] == 'total:']['discharged'].iloc[0]
            active_ = pd_table[pd_table['country'] == 'total:']['active'].iloc[0]
            critical_ = pd_table[pd_table['country'] == 'total:']['critical'].iloc[0]
            new_case_ = pd_table[pd_table['country'] == 'total:']['new_cases'].iloc[0]
            new_death_ = pd_table[pd_table['country'] == 'total:']['new_death'].iloc[0]

        #More info: https://github.com/Emmarex/dialogflow-fulfillment-python
        text1 = f'Currently, {country.capitalize()} has a total of {diagnose_:.0f} confirmed cases, + {new_case_:.0f} new case(s) from yesterday. There is total of {death_:.0f} death case(s), + {new_death_:.0f} new death case(s) from yesterday. \n\n{discharged_:.0f} people recovered from it, and {critical_:.0f} people still in critical condition. \n\n{LastUpdate}.'
   
    # --------------------------#
    # HEADLINE NEWS INTENT      #
    # --------------------------#
    if intent == "latest-news-covid":
        news_list = list(MOHHeadlines.objects.order_by('-news_date').values())
        metatext = "Below are the top 3 latest news:\n"
        for news in news_list[:3]: #top3
            date_ = news['news_date'].strftime('%d %b, %Y')
            title_ = news['news_title']
            link_ = news['news_link']
            metatext = metatext + f"{date_} \n{title_} \n{link_}\n\n"
        
        text1 = metatext + "For more info: https://www.moh.gov.sg/covid-19"
            
    
    # --------------------------#
    # Distance to Hospital      #
    # --------------------------#
    if intent == "nearest-hospital-covid":
        premise_ = req.get('queryResult').get('parameters').get('healthcare').capitalize()
        address_ = req.get('queryResult').get('parameters').get('address')
        
        if premise_ == '': premise_ = 'Hospital'
        print(premise_)

        #for testing only. Pick 5th from hospital/clinic list
        premise_query = list(hospitalList.objects.filter(Type=premise_))[5]
        result = gmaps.distance_matrix(str(address_) + ' Singapore', premise_query.address, departure_time=datetime.now())

        if result['rows'][0]['elements'][0]['status'] == 'NOT_FOUND':
            text1 = 'Route not found. Perhaps check your postal code?'
        else:
            distance_ = result['rows'][0]['elements'][0]['distance']['value']/1000 #convert m to km
            duration_ = result['rows'][0]['elements'][0]['duration']['value']/60 #convert sec to min
            text1 = f"Nearest {premise_} to you is at {premise_query.Name}. You are {distance_:.1f}km away from it, it will take approximately {duration_:.0f}min for you to reach there if you depart by car now."

    # --------------------------#
    # SYNC  INTENT              #
    # --------------------------#
    if intent == "sync":
        # try:
        ss = statusScrapper()
        ss.start()
        ns = newsScrapper()
        ns.start()
        text1 = "Sync/update completed."
        
        # except:
        #     text1="Error occurred. Contact admin to debug."



    dialogflow_response = DialogflowResponse(text1)
    reply = dialogflow_response.get_final_response()

    db.connections.close_all()
    # return generated response
    return HttpResponse(reply, content_type='application/json; charset=utf-8')

db.connections.close_all()