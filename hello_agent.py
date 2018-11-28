from pade.misc.utility import display_message, start_loop, call_in_thread
from pade.core.agent import Agent
from pade.acl.aid import AID
from pade.acl.messages import ACLMessage
from pade.behaviours.protocols import FipaSubscribeProtocol, TimedBehaviour
from sys import argv
import random
import time
import json
import datetime


def my_time(a, b):
    print('------> I will sleep now!', a)
    time.sleep(10)
    print('------> I wake up now!', b)


class SubscriberProtocol(FipaSubscribeProtocol):

    def __init__(self, agent, message):
        super(SubscriberProtocol, self).__init__(agent,
                                                 message,
                                                 is_initiator=True)
        self.agent = agent

    def handle_agree(self, message):
        display_message(self.agent.aid.name, message.content)

    def handle_inform(self, message):
        if self.agent.power:
                self.agent.power = False
                self.agent.max_power -= random.randint(10, 50)
                display_message(self.agent.aid.name, 'Turning lights off. Max power: {}'.format(self.agent.max_power))
        else:
            if self.agent.max_power >= 50:
                self.agent.power = True
                display_message(self.agent.aid.name, 'Turning lights on...')
            else:
                display_message(self.agent.aid.name, 'Insuficient power...')

class PublisherProtocol(FipaSubscribeProtocol):

    def __init__(self, agent):
        super(PublisherProtocol, self).__init__(agent,
                                                   message=None,
                                                   is_initiator=False)

    def handle_subscribe(self, message):
        self.register(message.sender)
        display_message(self.agent.aid.name, message.content)
        resposta = message.create_reply()
        resposta.set_performative(ACLMessage.AGREE)
        resposta.set_content('Subscribe message accepted')
        self.agent.send(resposta)

    def handle_cancel(self, message):
        self.deregister(self, message.sender)
        display_message(self.agent.aid.name, message.content)

    def notify(self, message):
        display_message(self.agent.aid.name, 'Attempting to send signal to lamps.')
        super(PublisherProtocol, self).notify(message)


class Time(TimedBehaviour):

    def __init__(self, agent, notify):
        super(Time, self).__init__(agent, 10)
        self.notify = notify
        self.agent = agent

    def on_time(self):
        super(Time, self).on_time()
        message = ACLMessage(ACLMessage.INFORM)
        message.set_protocol(ACLMessage.FIPA_SUBSCRIBE_PROTOCOL)
        message.set_content('Switch lights')
        self.notify(message)


class AgentSubscriber(Agent):

    def __init__(self, aid, message):
        super(AgentSubscriber, self).__init__(aid)
        self.max_power = 100
        self.power = False
        self.call_later(8.0, self.launch_subscriber_protocol, message)

    def launch_subscriber_protocol(self, message):
        self.protocol = SubscriberProtocol(self, message)
        self.behaviours.append(self.protocol)
        self.protocol.on_start()


class AgentPublisher(Agent):

    def __init__(self, aid):
        super(AgentPublisher, self).__init__(aid)

        self.protocol = PublisherProtocol(self)
        self.timed = Time(self, self.protocol.notify)

        self.behaviours.append(self.protocol)
        self.behaviours.append(self.timed)

        call_in_thread(my_time, aid.name, aid.name)

if __name__ == '__main__':

    agents_per_process = 1
    agents = list()
    port = 20000
    subscriber_index = 1
    for i in range(agents_per_process):        

        agent_name = 'agent_publisher_{}:{}'.format(i, port)
        agent_pub_1 = AgentPublisher(AID(name=agent_name))
        agents.append(agent_pub_1)
        port += 1

        msg = ACLMessage(ACLMessage.SUBSCRIBE)
        msg.set_protocol(ACLMessage.FIPA_SUBSCRIBE_PROTOCOL)
        msg.set_content('Subscription request')
        msg.add_receiver(agent_pub_1.aid)

        number_of_lamps = 3

        for l in range(number_of_lamps):
            agent_name = 'agent_subscriber_{}:{}'.format(subscriber_index, port)
            agent_sub = AgentSubscriber(AID(name=agent_name), msg)
            agents.append(agent_sub)
            port += 1
            subscriber_index += 1

            time.sleep(1)

    start_loop(agents)