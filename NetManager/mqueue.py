from collections import deque

class MessageQueue:

    def __init__(self):

        self.queue = deque()

    def add(self, hr, spo2):

        self.queue.append({
            "hr": hr,
            "spo2": spo2
        })

    def get(self):

        if len(self.queue) > 0:
            return self.queue.popleft()

        return None

    def empty(self):

        return len(self.queue) == 0