from extension.extension import Extension

class MediaExtension(Extension):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.read_match_function = lambda: False
        self.read_match_policy_level = -1

    def read_match_policy(self, level=0):

        def registry(function):
            if level > self.read_match_policy_level:
                self.read_match_function = function
                self.read_match_policy_level = level
            return function

        return registry

media_ext = MediaExtension()
