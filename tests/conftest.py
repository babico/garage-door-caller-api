import pytest
import tempfile
import os
import yaml


SAMPLE_PHONES_YAML = """
serials:
  qwerty123456qwerty123456:
    manufacturer: HUAWEI
    screen:
      width: 1080
      height: 2340
    wake_up: true
    swipe_unlock:
      start_x: 540
      start_y: 2000
      end_x: 540
      end_y: 500
      duration_ms: 300
    keypad_tap:
      x: 228
      y: 1937
    phone_pin: "123456"
  R58M42AXXXXX:
    manufacturer: DUMMY
    screen:
      width: 720
      height: 1280
    wake_up: false
    keypad_tap:
      x: 100
      y: 500
"""


@pytest.fixture
def phones_yaml_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(SAMPLE_PHONES_YAML)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def phones_config(phones_yaml_path):
    with open(phones_yaml_path) as f:
        return yaml.safe_load(f)
