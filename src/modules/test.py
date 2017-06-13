from threading import Thread, enumerate
import time

class ListThreads(Thread):
    def __init__(self):
        super().__init__()
        self.start()

    def run(self):
        x = 0
        while True:
            time.sleep(2)
            print()
            for thread in enumerate():
                print(thread)
            x = x + 1
            print(x)