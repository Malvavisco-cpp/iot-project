import json
import random
import sys

import util

class Node:
    def __init__(self,  prefix='UDFJC/emb1/robot0/', node_name=None):
        self.prefix=prefix
        self.subscriptions = {}  # topic -> set(callback)
        self.node_name  = node_name or prefix+str(random.randint(0,2**32-1))
        self.transports = []
        self.subscribe("node/get_second_ts",self.handle_get_second_ts )


    def add_transport(self, transport):
        self.transports.append(transport)
        for topic in self.subscriptions:
            transport.subscribe(topic)


    def publish(self, topic, msg):
        ts=util.time_float()
        for t in self.transports:
            t.publish(topic,msg)
        self.local_publish(topic,msg,ts=ts)

    def local_publish(self,topic,msg,ts=None):
        callbacks = self.subscriptions.get(topic, set())

        print(f"[INFO] [{ts}] [PUB {topic}] : {len(callbacks)} callbacks")

        for c in list(callbacks):
                try:
                    c(topic=topic,msg=msg)
                except Exception as e:
                    callbacks.remove(c)
                    print('msg error',msg)
                    print("Remove from topic",topic,"callback",c,"error")
                    sys.print_exception(e)


    def subscribe(self, topic,callback ):#topic without prefix
        self.subscriptions.setdefault(topic, set()).add(callback)
        for t in self.transports:
            t.subscribe(topic)

        print(f"[INFO] [] [SUB {callback}] : [{topic}]")

        self.publish(
            "node/new_sub",
            {
           "action": "SUB",
           "topic": self.prefix+topic,
        })

    def handle_get_second_ts(self, topic,msg):
        self.publish(
            "node/send_second_ts",
            {
                "topic": msg.get("topic"),
                "first_ts":  msg.get("first_ts"),
                "second_ts": util.time_float(),
                "sended": msg.get("sended")
            }
        )
