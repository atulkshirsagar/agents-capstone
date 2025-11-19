def custom_tool_function(param1, param2):
    # Example utility function that performs a custom operation
    return param1 + param2

class CustomTool:
    def __init__(self, name):
        self.name = name

    def execute(self, data):
        # Example method that processes data
        return f"{self.name} processed {data}"