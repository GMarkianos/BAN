from collections import deque

class MessageQueue:

    def __init__(self):

        self.queue = deque()

    def add(self, msg):

        self.queue.append(msg)

    def get(self):

        if len(self.queue) > 0:
            return self.queue.popleft()

        return None

    def empty(self):

        return len(self.queue) == 0