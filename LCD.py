#LCD API w display message functions 

import threading
from time import sleep, strftime
from datetime import datetime
from PCF import PCF8574_GPIO
from LCD_API import Adafruit_CharLCD

mcp = None
lcd = None
lcd_t = None 
terminate = False

display_request = None

def display_cimis_data(hour,temperature, humidity):
	message = "CIMIS Data " + str(hour) + ":00\nH:" + str(humidity) + " T:" + str(temperature)
	display_message(message)
def display_local_data(counter,temperature, humidity):
	message = "DHT Data #" + str(counter) + "\nH:" + str(humidity) + " T:" + str(temperature)
	display_message(message) 
def display_average_data(hour,temperature, humidity):
	message = "Avg Data " + str(hour) + ":00\nH:" + str(round(humidity)) + " T:" + str(round(temperature,1))
	display_message(message)   
    
#only called by display_cimis_data and display_local_data
def display_message(message):
	global display_request
	while(display_request is not None):
		sleep(1)
	display_request = message

def lcd_cleanup():
	global terminate
	global mcp
	terminate = True
	lcd_t.join()
	mcp.output(3,0) 	# turn off LCD backlight
	lcd.clear()
	
def lcd_setup():
	global lcd
	global lcd_t
	global terminate
	global mcp
	PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
	PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
	# Create PCF8574 GPIO adapter.
	try:
		mcp = PCF8574_GPIO(PCF8574_address)
	except:
		try:
			mcp = PCF8574_GPIO(PCF8574A_address)
		except:
			print ('I2C Address Error !')
		exit(1)
	# Create LCD, passing in MCP GPIO adapter.
	lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=mcp)

	mcp.output(3,1)     # turn on LCD backlight
	lcd.begin(16,2)     # set number of LCD lines and columns

	terminate = False
	lcd_t = threading.Thread(target = lcd_thread)
	lcd_t.daemon = True
	lcd_t.start()

#refresh the LCD with the current time every second

def lcd_thread():
	global display_request
	while not terminate:
		lcd.clear()
		lcd.setCursor(0, 0)
		if(display_request is not None):
			lcd.message(display_request)
			display_request = None
			sleep(5)
		else:
			lcd.message(datetime.now().strftime('   %Y-%m-%d') + "\n" + datetime.now().strftime('    %H:%M:%S'))
			sleep(1)
