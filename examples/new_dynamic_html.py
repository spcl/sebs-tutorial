from datetime import datetime
from random import sample
from os import path
from time import time
import logging
import os
from jinja2 import Template

from faker import Faker


SCRIPT_DIR = path.abspath(path.join(path.dirname(__file__)))


def handler(event):
    # Start overall timing
    start_time = time()

    logging.info("[INFO] Handler invoked")

    fake = Faker()

    # Extract and log inputs
    name = f'{event.get("username")}, email: {fake.email()}, working as {fake.job()}'
    size = event.get("random_len")
    cur_time = datetime.now()
    logging.info(f"[INFO] Username: {name}")
    logging.info(f"[INFO] Random count: {size}")

    # Time random number generation
    gen_start = time()
    random_numbers = sample(range(0, 1000000), size)
    gen_time = (time() - gen_start) * 1000000
    logging.info(f"[INFO] Generating {size} random numbers")

    # Render HTML template
    logging.info("[INFO] Rendering HTML template")
    render_start = time()
    template = Template(
        open(path.join(SCRIPT_DIR, "templates", "template.html"), "r").read()
    )
    html = template.render(
        username=name, cur_time=cur_time, random_numbers=random_numbers
    )
    render_time = (time() - render_start) * 1000000

    logging.info(f"[INFO] Generated HTML size: {len(html)} bytes")

    # Calculate total time
    logging.info("[INFO] Handler completed successfully")
    total_time = (time() - start_time) * 1000000

    return {
        'result': html,
        'measurement': {
            'generation_time': gen_time,
            'rendering_time': render_time,
            'total_time': total_time
        }
    }
