import logging

logger = logging.getLogger(__name__)


class BaseMiddleware:
    """
    Performs some sort of processing on inbound and outbound messages.
    """
    def __init__(self, name, *args, **kwargs):
        """
        :param name: A unique name that can be used to retrieve this middleware from the base
        message handler.
        """
        self.name = name

    def on_receive(self, message):
        """
        Override this method in order to define what to do when a message is received.

        :param message: Received message.
        :return: a processed message or None if message should not be processed any further.
        """
        return message

    def on_resend(self, message):
        """
        Override this message in order to define what to do when a message was not received successfully
        by the counter party.

        :param message: Message that was not received.
        :return: a processed message or None if message should not be processed any further.
        """
        return message

    def on_send(self, message):
        """
        Override this method in order to define what to do with a message needs to be transmitted.

        :param message: Message to be sent.
        :return: a processed message or None if message should not be processed any further.
        """
        return message


# class BaseSessionMiddleware(BaseMiddleware):
#     def __init__(self,
#                  name,
#                  sender=None,
#                  socket=None,
#                  socket_klass=None,
#                  heartbeat_time=1000,
#                  confirm_request_msg_count=100,
#                  reconnect=False,
#                  reconnect_time=60,
#                  send_period=0.1,
#                  low_priority=lambda _: True,
#                  extra_header_fields_fun=None,
#                  begin_string=b'FIXT.1.1',
#                  *args,
#                  **kwargs
#                  ):
#         super().__init__(name, *args, **kwargs)
#         if sender is None:
#             sender = settings.
#
#
#         self.we = we
#         self.heartbeat_time = heartbeat_time
#         self.confirm_request_msg_count = confirm_request_msg_count
#         self.reconnect = reconnect
#         self.reconnect_time = reconnect_time
#         self.waiting_for_confirmation = False
#         self.send_period = send_period
#         self.low_priority = low_priority
#         self.extra_header_fields_fun = extra_header_fields_fun
#         self.begin_string = begin_string
#
#         self.socket_klass = (lambda: socket) if socket else socket_klass
#
#         self.oms = None  # will be set in the out thread
#         self.next_in_seq_num = 1
#
#         self.gtfo = False  # get the fuck out
#
#         self.master_thread = self.MasterThread(app=self)
#         self.master_thread.start()
