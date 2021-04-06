#EECS 113 Final - main module
#Robert Chen (86266604)

#import from other modules
import RPi.GPIO as GPIO
import time
from datetime import datetime
import threading
import DHT as DHT
from CIMIS import get_cimis_data_for
from CIMIS import cimis_data
import LCD as LCD

GPIO.setwarnings(False)

#GPIO pin declaration
dhtPin = 11 #GPIO 17
pirPin = 22 #GPIO 25
irrigationPin = 33 #GPIO 13

dht = None
temp_array = [None]*24
humidity_array = [None]*24
starting_hour = -1

#data thread message
def console_msg1(message):
        print( datetime.now().strftime('[%H:%M:%S]') + "[Data thread] " + message )

#main func message
def console_msg2(message):
        print( datetime.now().strftime('[%H:%M:%S]') + "[Main thread] " + message )

#Setup 
def setup():
        global dht
        GPIO.setmode(GPIO.BOARD)           

        GPIO.setup(irrigationPin, GPIO.OUT, initial = GPIO.LOW) #Setup relay
        GPIO.setup(pirPin, GPIO.IN) #Setup pir
        dht = DHT.DHT(dhtPin)   #Setup dht
        LCD.lcd_setup() #Setup lcd
        
#Cleanup 
def cleanup():
        GPIO.output(irrigationPin, GPIO.LOW)
        LCD.lcd_cleanup()
        GPIO.cleanup()

#DHT gets temperature
def get_dht_temp():
        chk = None
        while (chk is not dht.DHTLIB_OK): 
                chk = dht.readDHT11()
        return dht.temperature

#DHT gets humidity
def get_dht_humidity():
        chk = None
        while (chk is not dht.DHTLIB_OK):
                chk = dht.readDHT11()
        return dht.humidity

#Thread func to get data
def get_data():
        current = starting_hour
        hours = 0
        #loop until 24 hours
        while (hours < 24):
                avg_temp = 0
                avg_humidity = 0
                for i in range (0,60,1): #get one hour of data
                        get_time = time.time()
                        local_humidity = get_dht_humidity()
                        local_temperature = get_dht_temp()
                        avg_temp = avg_temp + local_temperature
                        avg_humidity = avg_humidity + local_humidity
                        console_msg1("DHT data #"+ str(i+1) + ": Temp = " +  str(local_temperature) + " Humidity = " + str(local_humidity) ) 
                        LCD.display_local_data(i+1, local_temperature, local_humidity)
                        get_time = time.time() - get_time
                        if i is not 59:
                                time.sleep ( 60 - get_time )  #wait one minute
                        
                avg_temp = avg_temp/60
                avg_humidity = avg_humidity/60

                #calculate average of hourly data and store in array for tracking/display
                console_msg1("Computing hourly local averages...")
                print("Avg Temp = " + str(round(avg_temp,1)) + " Avg Humidity = " + str(round(avg_humidity)) )
                LCD.display_average_data(current, avg_temp, avg_humidity)
                temp_array[current] = avg_temp
                humidity_array[current] = avg_humidity
                print("Local temperature averages: ") #display all hourly DHT temperature averages
                print(temp_array)
                print("Local humidity averages: ") #display all hourly DHT humidity averages
                print(humidity_array)
                time.sleep ( 60 - get_time ) 
                current = (current+1) % 24
                hours = hours + 1

#Main loop of program, get CIMIS data and determine irrigation time
def mainloop():
        current = starting_hour
        hours = 0
        time.sleep(3600)
        delay = 0
        #begin irrigation loop
        while (hours < 24):
                hour_delay = time.time()
                console_msg2("Getting CIMIS data for time " + str(current) + ":00")

                #Retrieve the cimis data for the past hour, recursively loop if CIMIS data is not updated on website for the hour
                data = get_cimis_data_for(current)            
                while(data is None or data.get_humidity() is None or data.get_temperature() is None):
                        if data is None:
                                console_msg2("Error occured while fetching CIMIS data. Trying again next hour")
                        else:
                                console_msg2("Cimis data not yet available. Trying again next hour")
                        time.sleep(3600)        #thread waits 1 hour
                        console_msg2("Getting CIMIS data for time " + str(current) + ":00")
                        data = get_cimis_data_for(current) #recursively loop until successful CIMIS data retrieval

                #display the CIMIS data for the hour
                console_msg2("Cimis data for " + str(current) + ":00 is: ")
                print("Humidity = " + data.get_humidity(), 
                          " Temperature = "+ data.get_temperature() + " Eto = "+ data.get_eto())
                LCD.display_cimis_data(current, data.get_temperature(), data.get_humidity())

                #Retrieve the local data, recursively call if local data not ready to be calculated yet
                while(temp_array[current] is None or humidity_array[current] is None):
                        console_msg2("Local data for time "+ str(current) + ":00 not available. Trying again in 1 minute")
                        time.sleep(60) #waits 1 minute

                local_temp = temp_array[current] 
                local_humidity = humidity_array[current]
                console_msg2("Local data for "+ str(current) + ":00, Avg Temp = " + str(round(local_temp,2)) + " Avg Humidity = " + str(round(local_humidity)) )
                
                #Calculate irrigation time
                time_to_irrigate = get_time_to_irrigate(data, local_temp, local_humidity)

                #irrigation execution, stall if motion is detected during irrigation
                if time_to_irrigate == 0 :
                        console_msg2("No eto for time "+ str(current) + ":00. No irrigation this hour")
                else:
                        console_msg2("Turning on irrigation for " + str(time_to_irrigate) + " seconds...")
                        GPIO.output(irrigationPin, GPIO.HIGH)
                        start_time = time.time()
                        stall = 0
                        while(time.time() < start_time + time_to_irrigate + stall):
                                if(GPIO.input(pirPin) == GPIO.HIGH and stall < 60):
                                        console_msg2("Motion detected. Stalling irrigation for 5 seconds") #motion stalls irrigation (BLUE led on for pir sensor, YELLOW led for irrigation off)
                                        GPIO.output(irrigationPin,GPIO.LOW)
                                        time.sleep(5)
                                        stall = stall + 5
                                        GPIO.output(irrigationPin,GPIO.HIGH)
                                        
                        console_msg2("Irrigation done for hour " + str(current) + ":00. Turning off irrigation.") #irrigation finishes for the hour, yellow LED off
                        GPIO.output(irrigationPin, GPIO.LOW)

                #Irrigation complete for hour
                current = (current+1) % 24
                hours = hours + 1

                hour_delay = time.time() - hour_delay
                delay = delay + hour_delay

                if(delay < 3600):
                        time.sleep(3600 - delay)
                        delay = 0
                else:
                        delay = delay - 3600


#returns irrigation time based on calculations
def get_time_to_irrigate(data, local_temperature, local_humidity):
        PF = 1.0  #plant factor for grass
        SF = 200 #area to irrigate (sq ft)
        IE = 0.75 #irrigation efficiency 
        WD = 1020 #water per hour (gallons per hour)
        
        modified_eto = float(data.get_eto())*(float(data.get_humidity())/local_humidity)*(local_temperature/float(data.get_temperature())) #formula for calculating new eto
 
        gallons_needed_per_hour = modified_eto * PF * SF * 0.62 / IE / float(24)  #gallons needed per hour
        time_needed = gallons_needed_per_hour / WD #irrigation time 

        return time_needed * 3600 #hour

#main program
if __name__ == '__main__':
        t = None

        try:
                print("Program started at",time.strftime( "%H:%M:%S" ,time.localtime(time.time())) )
                starting_hour = time.localtime(time.time()).tm_hour

                #setup GPIO and fetch data
                setup()
                t = threading.Thread(target = get_data)
                t.daemon = True
                console_msg2("Starting thread to fetch data")
                t.start()

                mainloop()
                t.join()

        finally:
                cleanup()
