"""
The Progress Bar code written by Joey Payne
see here: http://pythoncentral.io/how-to-movecopy-a-file-or-directory-folder-with-a-progress-bar-in-python/
"""


class ProgressBar:
    def __init__(self, width=20, progress_symbol="▓", empty_symbol="░"):
        self.width = width

        if self.width < 0:
            self.width = 0

        self.progress_symbol = progress_symbol
        self.empty_symbol = empty_symbol

    def update(self, progress):
        total_blocks = self.width
        filled_blocks = int(round(progress / (100 / float(total_blocks))))
        empty_blocks = total_blocks - filled_blocks

        progress_bar = self.progress_symbol * filled_blocks + self.empty_symbol * empty_blocks

        return f"{progress_bar} {progress}%"
