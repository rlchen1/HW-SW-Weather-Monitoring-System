#CIMIS data retrieval API

from __future__ import print_function
import json
from urllib.request import urlopen
import urllib
from datetime import datetime, timedelta
import time

station = 75    #Irvine
appKey = 'a7a8f709-6f0d-4a3e-b72b-684ec03c7cab'

class cimis_data:
    def __init__(self, date, hour, humidity, temperature, eto):
        self.date = date 
        self.hour = hour
        self.humidity = humidity
        self.temperature = temperature
        self.eto = eto
    def get_date(self):
        return self.date
    def get_hour(self):
        return self.hour
    def get_humidity(self):
        return self.humidity
    def get_temperature(self):
        return self.temperature
    def get_eto(self):
        return self.eto
    
def get_cimis_data_for (current_hour):
    if current_hour == 0 or current_hour > time.localtime(time.time()).tm_hour:
        date = datetime.strftime(datetime.now() - timedelta(1), '%Y-%m-%d')
    else:
        date = datetime.now().strftime('%Y-%m-%d')

    data = run_cimis(appKey, station, date, date)
    if data is None:
        return None

    d = cimis_data( data[current_hour-1]['Date'],     
                    data[current_hour-1]['Hour'], 
                    data[current_hour-1]['HlyRelHum']['Value'],
                    data[current_hour-1]['HlyAirTmp']['Value'],
                    data[current_hour-1]['HlyEto']['Value']
                   )
    return d
   
def print_table(data):
    print('---------------------------------------------')
    print('  Date\t\tHour\tHumid\tTemp\tEto')
    print('\t\t(PST)\t(%)\t(C)\t(mm)')
    print('---------------------------------------------')
    for i in range(0, 24):
        print( data[i]['Date'], '\t',
               data[i]['Hour'], '\t', 
               data[i]['HlyRelHum']['Value'], '\t',
               data[i]['HlyAirTmp']['Value'], '\t',
               data[i]['HlyEto']['Value']
             )
     
def retrieve_cimis_data(url, target):
    try:
        content = urlopen(url).read().decode('utf-8')        
        assert(content is not None)
        return json.loads(content)
    except urllib.error.HTTPError as e:
        print("Could not resolve the http request at this time")
        error_msg = e.read()
        print(error_msg)
        return None
    except urllib.error.URLError:
        print('Could not access the CIMIS database.Verify that you have an active internet connection and try again.')
        return None
    except: #json.decoder.JSONDecodeError:  #ConnectionResetError:
        print("CIMIS request was rejected")
        return None
 
def run_cimis(appKey, station, start, end):
    ItemList = ['hly-air-tmp',
                'hly-eto',
                'hly-rel-hum']

    dataItems = ','.join(ItemList)
    
    url = ('http://et.water.ca.gov/api/data?appKey=' + appKey + '&targets='
            + str(station) + '&startDate=' + start + '&endDate=' + end +
            '&dataItems=' + dataItems +'&unitOfMeasure=M')        
    data = retrieve_cimis_data(url, station)
    if(data is None):
        return None    
    else:
        return data['Data']['Providers'][0]['Records']
