import paho.mqtt.client as mqtt
import datetime
import logging as log
import cfg
from time import sleep,time
import json
import rules
import socket
from vectors import Vector

# -------------------- mqtt events -------------------- 
def on_connect(lclient, userdata, flags, rc):
    log.info("mqtt connected with result code "+str(rc))
    for rule_name,rule in config["rules"].items():
        if(rule["enable"]):
            log.info("Subscription for rule:%s %s -> %s",rule_name,rule["input"],rule["output"])
            lclient.subscribe(rule["input"])
    #Here custom subscriptions can be added
    lclient.subscribe("jNodes/+/alive")

def get_min_rssi(j_payload):
    res = None
    for key, value in j_payload.items():
        if key.startswith('rx'):
            if 'rssi' in value:
                rssi = int(value["rssi"])
                if(res is None) or (res > rssi):
                    res = rssi
    return res

def on_message(client, userdata, msg):
    topic_parts = msg.topic.split('/')
    for rule_name,rule in config["rules"].items():
        if msg.topic == rule["input"]:
            if(rule["enable"]):
                #call the Fuction with the same name as the Rule 
                payload = getattr(rules,rule_name)(msg.payload)
                #payload = rules.Upstairs_Heat(msg.payload)
                if(payload != None):
                    clientMQTT.publish(rule["output"],payload)
    #Here Custom Rules can be run
    if (len(topic_parts)==3) and (topic_parts[0] == "jNodes") and (topic_parts[2]=="alive"):
        j_payload = json.loads(msg.payload)
        min_rssi = get_min_rssi(j_payload)
        min_rssi_text = json.dumps(min_rssi)
        if(min_rssi_text != None):
            topic = "Nodes/"+topic_parts[1]+"/rssi"
            clientMQTT.publish(topic,min_rssi_text)


def ruler_loop_forever():
    while(True):
        sleep(10)
    return


def mqtt_start():
    def mqtt_connect_retries(client):
        connected = False
        while(not connected):
            try:
                client.connect(config["mqtt"]["host"], config["mqtt"]["port"], config["mqtt"]["keepalive"])
                connected = True
                log.info(  "mqtt connected to "+config["mqtt"]["host"]+":"+str(config["mqtt"]["port"])+" with id: "+ cid )
            except socket.error:
                log.error("socket.error will try a reconnection in 10 s")
                sleep(10)
        return
    cid = config["mqtt"]["client_id"] +"_"+socket.gethostname()
    client = mqtt.Client(client_id=cid)
    clientMQTT = mqtt.Client()
    clientMQTT.on_connect = on_connect
    clientMQTT.on_message = on_message
    mqtt_connect_retries(clientMQTT)
    clientMQTT.loop_start()
    return clientMQTT




# -------------------- main -------------------- 
config = cfg.configure_log(__file__)

#will start a separate thread for looping
clientMQTT = mqtt_start()

#loop forever
ruler_loop_forever()


