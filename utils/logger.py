import logging
from rich.logging import RichHandler
from rich.console import Console

def get_logger(name: str = "dockerforge") -> logging.Logger:
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        console_handler = RichHandler(
            rich_tracebacks=True,
            markup=True,
            show_path=False
        )
        # console_handler.setLevel(logging.INFO)
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        log_file = "dockerforge.log"
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG) 
        
        class StripMarkupFormatter(logging.Formatter):
            def __init__(self, fmt=None, datefmt=None):
                super().__init__(fmt, datefmt)
                self.console = Console(color_system=None) 

            def format(self, record):
                formatted = super().format(record)
                
                with self.console.capture() as capture:
                    self.console.print(formatted, end="")
                return capture.get()

        file_formatter = StripMarkupFormatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    return logger

logger = get_logger()
