import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import influxdb
import requests
import datetime
import logging as log
import cfg
from time import sleep
import socket
import json
from mqtt import mqtt_start
import dateutil.parser

def last_seen_fresh(last_seen_text):
    last_seen_time = dateutil.parser.parse(last_seen_text).replace(tzinfo=None)
    diff = datetime.datetime.now() - last_seen_time
    if(diff.total_seconds() > 2):
        return False
    else:
        return True
# -------------------- mqtt events -------------------- 
def mqtt_on_message(client, userdata, msg):
    topic_parts = msg.topic.split('/')
    try:
        post = None
        if( (len(topic_parts) == 3) and (topic_parts[0] == "Nodes") ):
            nodeid = topic_parts[1]
            sensor = topic_parts[2]
            measurement = "node"+nodeid
            value = float(str(msg.payload))
            post = [
                {
                    "measurement": measurement,
                    "time": datetime.datetime.utcnow(),
                    "fields": {
                        sensor: value
                    }
                }
            ]
        elif( len(topic_parts) == 2 ):
            sensor = topic_parts[1]
            fields = json.loads(msg.payload)
            
            if("pressure" in fields):
                fields["pressure"] = int(fields["pressure"]) #force pressure to int
            if("voltage" in fields):
                fields["voltage"] = float(fields["voltage"])/1000 #convert voltage from milivolts to Volts
            if("temperature" in fields):
                fields["temperature"] = float(fields["temperature"]) #force temperature to float
            if("humidity" in fields):
                fields["humidity"] = float(fields["humidity"]) #force humidity to float
            if("battery" in fields):
                fields["battery"] = int(fields["battery"]) #force battery to int
            is_last_seen_relevant = False
            if("last_seen" in fields):
                is_last_seen_relevant = True
                last_seen = fields["last_seen"]
                del fields["last_seen"]
                is_last_seen_fresh = last_seen_fresh(last_seen)
            if(is_last_seen_relevant) and (not is_last_seen_fresh):
                log.info("postdiscarded from "+sensor+" last seen at "+last_seen)
            else:
                post = [
                    {
                        "measurement": sensor,
                        "time": datetime.datetime.utcnow(),
                        "fields": fields
                    }
                ]
        if(post != None):
            try:
                clientDB.write_points(post)
                log.debug(msg.topic+" "+str(msg.payload)+" posted")
            except requests.exceptions.ConnectionError:
                log.error("ConnectionError sample skipped "+msg.topic)
            except influxdb.exceptions.InfluxDBServerError:
                log.error("InfluxDBServerError sample skipped "+msg.topic)
            except influxdb.exceptions.InfluxDBClientError as e:
                log.error("InfluxDBClientError with "+msg.topic+" : " +str(msg.payload)+" >>> "+str(e) )
    except ValueError:
        log.error(" ValueError with : "+msg.topic+" "+str(msg.payload))

# -------------------- main -------------------- 
config = cfg.configure_log(__file__)

# -------------------- influxDB client -------------------- 
clientDB = InfluxDBClient(    config["influxdb"]["host"], 
                            config["influxdb"]["port"], 
                            'root', 'root', 
                            config["influxdb"]["db"])
#clientDB.create_database(config["influxdb"]["db"])

# -------------------- Mqtt Client -------------------- 
#will start a separate thread for looping
clientMQTT = mqtt_start(config,mqtt_on_message,True)

while(True):
    sleep(0.2)
    #The MQTT keeps looping on a thead
    #All there is to do here is not to exit
