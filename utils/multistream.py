class MultiStream:
    def __init__(self, *streams):
        self.streams = streams


    def write(self, data):
        for stream in self.streams:
            stream.write(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

