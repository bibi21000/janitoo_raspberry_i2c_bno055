.. image:: https://travis-ci.org/bibi21000/janitoo.svg?branch=master
    :target: https://travis-ci.org/bibi21000/janitoo
    :alt: Travis test status

.. image:: https://travis-ci.org/bibi21000/janitoo.svg?branch=v0.0.6
    :target: https://travis-ci.org/bibi21000/janitoo
    :alt: Travis production status

=======
janitoo
=======

janitoo is a mqtt protocol for Home Automation



Topics

/dhcp/lease/new
/dhcp/lease/repair
/dhcp/lease/lock
/dhcp/lease/remove
/dhcp/lease/release
/dhcp/heartbeat#
/dhcp/resolv/hadd
/dhcp/resolv/name
/dhcp/resolv/cmd_classes

/request/nodes/HADDController : controller should also listen to this topic.
/request/broadcast : all controllers should listen to the broadcast topic. At now, it is only used by system values to discover network.
/reply/nodes/HADDClient : when they receive a request, controller should send response here to the HADD client address
/reply/broadcast/HADDClient : when they receive a request, controller should send response here to the HADD client address

/request/dhcp/heartbeat : the dhcp server should liste to this. It should send a reply with all known nodes and theirs states.
/reply/dhcp/hearbeat/HADDClient : This this where the dhcp server should send the reply.

#To speak to the machines
/machines/#HADD#

#To retrieve informatations on values
/values/infos
#To get updated data of values
/values/data

#To retrieve informatations on nodes
/nodes/infos
#To get values of a node
/nodes/values

#HADD#

/dhcp/#', callback=self.mqtt_on_message)


Todo :
add hadd or rename node_uuid in values. We must be abblet to contact the


From arduino to android

arduino --- mqtt ---> mosquitto ----- mqtt-----> janitoo_socketio ------- socket.io ------> android
                          ^                               |
                          |                               +-------------- socket.io ------> webapp
raspberry - mqtt ---------+


We will integrate the socketio and the webapp in a flask application.
It should be a good idea to separate them, but this will add a lot of configuration problems :

 - must use 2 ports : one for the socketio and one for the webapp -> 2 configurations options in clients and server.
 - what about internet access : must use apache or nginx to add security : but need to update config on the fly or use some dns hack.
 - ...

So ... a single webapp.

The listener/socket.io will handle the nodes and values received from info request.

mqtt
====

We should minimize the traffic between publishers and subscribers and the number of needed coonections.

Topics added to a mqtt client must be under the tre of the topic we subsribe to (ie to listen to topics /nodes and /broadcast, we must subscribe to /)
But we will receive all the traffic of the queue

The broadcast :
we should use a special mqtt_client and subscribe to /broadcast topic

The nodes and controllers :
if we want to minimize traffic, nodes and crontroller should subscribe to /nodes/hadd. So all device need its own publisher.

to minimize connections, they should subscribe to /nodes. But in this case we will receive all the traffic for all nodes.

A simple (not simple with dhcp) is to listen to /nodes/add_ctrl/# :

 - we can talk to the controller using /nodes/add_ctrl/# or /nodes/add_ctrl/0000/#
 - for controller that need a dedicated topic, it can add it /nodes/add_ctrl/XXXX/#

It can

/broadcast/request
/broadcast/reply

/nodes/HADD/request
/nodes/HADD/reply

/nodes

/values

