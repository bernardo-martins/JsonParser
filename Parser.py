import json
import collections
import re

class StreamingJSONParser:
    def __init__(self):
        self.state = {}
        # Tracks the current key and value being processed
        self.current_key = None
        self.position = 0
        self.current_value = None
        # Buffer to accumulate partial input data
        self.buffer = ""
        # Regular expressions to match keys and string values
        self.key_pattern = r'"(.*?)":'  # Match any key enclosed in double quotes
        self.string_value_pattern = r'"(.+)"'  # Match complete strings (quoted)
        self.incomplete_string_pattern = r'"([^"].+)$'  # Match incomplete strings (no closing quote)
        self.non_string_value_pattern = r'\d+'  # Match non-string values
        self.empty_string_value_pattern = r'""'

    def _parse_key(self, data):
        """ Extract the key using regex. """
        match = re.search(self.key_pattern, data)
        if match:
            return match.group(1), match.end()
        return None, 0

    def _parse_new_json(self, data):
        match = re.search(r'\{.*?\}', data)
        if match:
            return match.group(0), match.end()
        return None, 0

    def _parse_string(self, data):
        """ Extract the string value using regex, handling both complete and incomplete strings. """
        # Try to find a complete string first
        match = re.search(r'"(.*?)"(?![^"]*":)', data)
        if match:
            return match.group(1), match.end()  # Full string matched
        return None, 0

    def _parse_incomplete_string(self, data):
        """ Extract the incomplete string value using regex. """
        match = re.search(self.incomplete_string_pattern, data)
        if match:
            return match.group(1), match.end()
        return None, 0

    def _parse_empty_string(self, data):
        """ Extract the empty string value using regex. """
        match = re.search(self.empty_string_value_pattern, data)
        if match:
            return match.end()
        return None, 0

    def _parse_non_string_value(self, data):
        """ Extract non-string values (numbers, booleans, null) using regex. """
        match = re.search(self.non_string_value_pattern, data)
        if match:
            return match.group(0), match.end()
        return None, 0

    def _parse_string_continuation(self, data):
        """ Extract the string value using regex, handling both complete and incomplete strings. """
        # Try to find a complete string first
        match = re.search(r'(?<!")\b[A-Za-z0-9]+\b(?!")', data)
        if match:
            return match.group(0), match.end()
        return None, 0

    def _parse_ending_string(self, data):
        """ Extract the string value using regex, incomplete strings. """
        # Try to find a complete string first
        print("data to parse_ending_string :",data)
        match = re.search(r'[A-Za-z0-9]+(?=")', data)
        if match:
            return match.group(0), match.end()
        return None, 0

    def convert_to_true_type(self, value):
        # Check if the value is an integer
        if value.isdigit():  # Only works for non-negative integers
            return int(value)

        # Check if the value is a float (this is a basic check, more robust checks can be added)
        try:
            return float(value)
        except ValueError:
            pass  # Not a float

        # If it's none of the above, assume it's a string
        return value


    def consume(self, chunk):
        """ Process incremental chunks of the input data. """
        self.buffer += chunk
        print("+++++++++++++++++++++++++ initial buffer "+ self.buffer+" +++++++++++++++++++++++++")
        while self.position < len(self.buffer):
            if self.current_key is None:
                # Parse key
                key, key_end = self._parse_key(self.buffer[self.position:])
                if key:
                    self.state[key] = ""
                    self.current_key = key
                    self.position += key_end
                else:
                    self.position += 1

            if self.current_value is not None and self.current_key is not None:
                value, value_end = self._parse_ending_string(self.buffer[self.position:])
                if value:
                    self.state[self.current_key] += str(value)
                    self.current_key = None
                    self.current_value = None
                    self.position += value_end
                    continue

                value, value_end = self._parse_string_continuation(self.buffer[self.position])
                if value:
                    self.state[self.current_key] += str(value)
                    self.position += value_end
                    continue

            if self.current_value is None:
                # Parse empty string
                value_end = self._parse_empty_string(self.buffer[self.position:])
                if isinstance(value_end, int):
                    self.position += value_end

                value, value_end = self._parse_new_json(self.buffer[self.position:])
                if value:
                    # If the value is found, store it in the state and reset the key and value
                    parser = StreamingJSONParser()
                    self.state[self.current_key] += str(parser.consume(self.buffer[self.position:]))
                    self.position += value_end
                    self.current_key = None
                    self.current_value = None
                    continue

                # Parse string or non-string value
                value, value_end = self._parse_string(self.buffer[self.position:])
                if value:
                    # If the value is found, store it in the state and reset the key and value
                    self.state[self.current_key] = value
                    self.current_key = None
                    self.current_value = None
                    self.position += value_end
                    continue

                value, value_end = self._parse_incomplete_string(self.buffer[self.position:])
                if value:
                    # If the value is found, store it in the state and reset the key and value
                    self.state[self.current_key] = value
                    self.current_value = value
                    self.position += value_end
                    continue

                value, value_end = self._parse_non_string_value(self.buffer[self.position:])
                print(self.buffer[self.position:])
                if value:
                    # If the value is found, store it in the state and reset the key and value
                    self.state[self.current_key] = self.convert_to_true_type(value)
                    self.current_key = None
                    self.current_value = None
                    self.position += value_end

        return self.state


    def get(self):
        """ Return the current state of the parsed JSON object. """
        return self.state


# Example usage:
parser = StreamingJSONParser()
parser.consume('{"test": "s')

print(parser.get())

parser.consume('aaa')
print(parser.get())